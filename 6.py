import os
import pandas as pd
import subprocess

# 入力と出力のフォルダ
INPUT_FOLDER = "parameter"
OUTPUT_FOLDER = "output_tfvars"
OUTPUT_FILE = "output.tfvars"

def dict_to_hcl(data):
    """辞書をHCL形式に変換"""
    def format_value(value):
        if isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, list):
            formatted_list = ",\n".join(format_value(v) for v in value)
            return f"[\n{formatted_list}\n]"
        elif isinstance(value, dict):
            formatted_dict = ",\n".join(
                f'{key} = {format_value(val)}' for key, val in value.items()
            )
            return f"{{\n{formatted_dict}\n}}"
        else:
            return str(value)

    formatted = ",\n".join(f'{key} = {format_value(val)}' for key, val in data.items())
    return formatted

def ensure_list(current, index):
    """
    currentがリストでない場合、リストに変換し、必要に応じてサイズを拡張。
    """
    if not isinstance(current, list):
        # currentが辞書やNoneの場合でもリストに変換
        current = [{} for _ in range(index + 1)]
    while len(current) <= index:
        # リストのサイズを拡張
        current.append({})
    return current

def handle_nested_keys(current, keys, value):
    """
    指定されたキーを元にネストされた辞書/配列を構築。
    """
    for key in keys[:-1]:  # 最終キー以外でループ
        if key.isdigit():  # 配列インデックスの場合
            key = int(key)
            current = ensure_list(current, key)  # 必要に応じてリスト変換
            current = current[key]
        else:
            current = current.setdefault(key, {})  # 辞書として処理

    # 最終キーに値を設定
    final_key = keys[-1]
    if final_key.isdigit():  # 配列インデックスの場合
        final_key = int(final_key)
        current = ensure_list(current, final_key)  # 必要に応じてリスト変換
        current[final_key] = value
    else:
        current[final_key] = value

def process_excel_file(file_path):
    """Excelファイルを読み込み、tfvars形式に整形する"""
    tfvars_data = {}

    with pd.ExcelFile(file_path) as xls:
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            if not {"resource", "arguments", "value", "generate_tfvars_flag"}.issubset(df.columns):
                print(f"Missing required columns in sheet: {sheet_name}")
                continue

            # フラグがTrueの行のみ処理
            filtered_df = df[df["generate_tfvars_flag"] == True]
            for resource, group in filtered_df.groupby("resource"):
                resource_data = tfvars_data.setdefault(resource, {})
                for _, row in group.iterrows():
                    keys = row["arguments"].split(".")
                    value = row["value"]
                    # 値が文字列の数値の場合、数値型に変換
                    if isinstance(value, str) and value.isdigit():
                        value = int(value)
                    handle_nested_keys(resource_data, keys, value)

    print(f"Processed data for {file_path}: {tfvars_data}")  # デバッグ用出力
    return tfvars_data

def save_tfvars(data):
    """tfvars形式でデータを保存し、terraform fmtを実行"""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    output_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)

    with open(output_path, "w") as f:
        f.write(dict_to_hcl(data))

    try:
        subprocess.run(["terraform", "fmt", output_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running terraform fmt: {e}")
        print(f"File content:\n{open(output_path).read()}")
        raise

def main():
    """メイン処理"""
    all_tfvars = {}

    # フォルダ内の全Excelファイルを処理
    for file_name in os.listdir(INPUT_FOLDER):
        if file_name.endswith(".xlsx"):
            print(f"Processing file: {file_name}")  # ファイル名を表示
            file_path = os.path.join(INPUT_FOLDER, file_name)
            tfvars_data = process_excel_file(file_path)
            all_tfvars.update(tfvars_data)

    print(f"Collected tfvars data: {all_tfvars}")  # デバッグ用出力

    if all_tfvars:
        save_tfvars(all_tfvars)
        print("TFVars file saved successfully.")
    else:
        print("No data to save.")
