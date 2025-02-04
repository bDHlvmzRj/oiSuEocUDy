import os
import re
import pandas as pd
import subprocess

# -------------------------------
# Excelのセル値を適切な型に変換する関数
def parse_value(val):
    """
    Excelから読み込んだ値を適切な型に変換する。
    例："20" -> 20, "gp3" -> "gp3", "True" -> True
    """
    if isinstance(val, str):
        val_strip = val.strip()
        # ブール値の場合
        if val_strip.lower() == "true":
            return True
        if val_strip.lower() == "false":
            return False
        # 数値変換を試みる
        try:
            int_val = int(val_strip)
            return int_val
        except ValueError:
            try:
                float_val = float(val_strip)
                return float_val
            except ValueError:
                return val_strip
    else:
        return val

# -------------------------------
# キー文字列からネストされた辞書へ値をセットする関数
def set_nested_value(d, key_str, value):
    """
    キー文字列（例："root_block_device[0].volume_size" や "tags.Name"）を
    分解し、辞書dに対してネストした構造としてvalueを設定する。
    """
    parts = key_str.split(".")
    current = d
    for i, part in enumerate(parts):
        # キー名とインデックスを正規表現で抽出
        m = re.match(r"(\w+)(?:\[(\d+)\])?", part)
        if not m:
            continue
        key = m.group(1)
        index = m.group(2)

        # 最終要素の場合は値をセット
        if i == len(parts) - 1:
            if index is not None:
                idx = int(index)
                if key not in current or not isinstance(current[key], list):
                    current[key] = []
                while len(current[key]) <= idx:
                    current[key].append(None)
                current[key][idx] = value
            else:
                current[key] = value
        else:
            if index is not None:
                idx = int(index)
                if key not in current or not isinstance(current[key], list):
                    current[key] = []
                while len(current[key]) <= idx:
                    current[key].append({})
                if current[key][idx] is None:
                    current[key][idx] = {}
                current = current[key][idx]
            else:
                if key not in current or not isinstance(current[key], dict):
                    current[key] = {}
                current = current[key]

# -------------------------------
# プリミティブ型の値をHCL形式へ変換する関数
def format_primitive(val):
    """
    文字列、数値、ブール値をHCL形式の文字列へ変換する。
    文字列はダブルクオートで囲む。ブールは小文字で出力する。
    """
    if isinstance(val, bool):
        return "true" if val else "false"
    elif isinstance(val, (int, float)):
        return str(val)
    else:
        return f'"{val}"'

# -------------------------------
# 辞書型をHCL形式の文字列へ変換する再帰関数
def dict_to_hcl(d, indent=0):
    """
    dict型をHCL形式の文字列へ変換する。
    """
    lines = []
    indent_str = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f'{indent_str}{k} = {{')
            lines.append(dict_to_hcl(v, indent + 1))
            lines.append(f'{indent_str}}}')
        elif isinstance(v, list):
            lines.append(f'{indent_str}{k} = {list_to_hcl(v, indent)}')
        else:
            lines.append(f'{indent_str}{k} = {format_primitive(v)}')
    return "\n".join(lines)

# -------------------------------
# リスト型をHCL形式の文字列へ変換する再帰関数
def list_to_hcl(lst, indent=0):
    """
    list型をHCL形式の文字列へ変換する。
    リストの要素がdictの場合は中括弧ブロックとして出力する。
    """
    indent_str = "  " * indent
    inner_indent = "  " * (indent + 1)
    lines = ["["]
    for item in lst:
        if isinstance(item, dict):
            lines.append(f'{inner_indent}' + "{")
            lines.append(dict_to_hcl(item, indent + 2))
            lines.append(f'{inner_indent}' + "},")
        elif isinstance(item, list):
            lines.append(f'{inner_indent}{list_to_hcl(item, indent + 1)},')
        else:
            lines.append(f'{inner_indent}{format_primitive(item)},')
    lines.append(f'{indent_str}]')
    return "\n".join(lines)

# -------------------------------
# メイン処理
def main():
    # 入力Excelファイルが格納されているフォルダ
    input_folder = "parameter"
    # 出力先フォルダ
    output_folder = "output_tfvars"
    os.makedirs(output_folder, exist_ok=True)
    # 出力tfvarsファイルのパス
    output_file = os.path.join(output_folder, "output.tfvars")

    # 最終的なtfvars用データを格納する辞書
    tfvars_data = {}

    # os.listdirでファイル一覧を取得
    for filename in os.listdir(input_folder):
        # 拡張子が.xlsxのファイルのみを対象とする
        if not filename.lower().endswith(".xlsx"):
            continue
        excel_path = os.path.join(input_folder, filename)
        # Windows環境では、Excelファイルの読み込み時に openpyxl を指定する
        xls = pd.ExcelFile(excel_path, engine="openpyxl")
        for sheet_name in xls.sheet_names:
            # シート名をキーとして、最上位のネストは「シート名_list」とする
            top_key = sheet_name + "_list"
            if top_key not in tfvars_data:
                tfvars_data[top_key] = {}
            # シートをDataFrameとして読み込み
            df = pd.read_excel(xls, sheet_name=sheet_name)
            # 各行について、「gen-tfvars-flag」がTrueの場合のみ処理する
            for idx, row in df.iterrows():
                flag = str(row.get("gen-tfvars-flag", "")).strip().lower()
                if flag != "true":
                    continue  # tfvarsに反映しない行はスキップ

                resource_name = str(row.get("resource-name")).strip()
                arguments = str(row.get("arguments")).strip()
                raw_value = row.get("value")
                value = parse_value(raw_value)

                # 同一リソース名ごとにパラメータをグループ化する
                if resource_name not in tfvars_data[top_key]:
                    tfvars_data[top_key][resource_name] = {}
                # ネスト構造の辞書へ値をセット
                set_nested_value(tfvars_data[top_key][resource_name], arguments, value)

    # -------------------------------
    # tfvars用HCL形式の文字列へ変換
    hcl_lines = dict_to_hcl(tfvars_data, indent=0)

    # 出力ファイルへ書き込み
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(hcl_lines)

    # -------------------------------
    # 出力後、terraform fmt を実行する
    try:
        subprocess.run(["terraform", "fmt", output_file], check=True)
        print(f"tfvarsファイルを整形しました: {output_file}")
    except Exception as e:
        print("terraform fmt の実行に失敗しました。TerraformがPATHに含まれているか確認してください。")
        print(e)

if __name__ == "__main__":
    main()
