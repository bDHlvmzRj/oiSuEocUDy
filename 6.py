import os
import pandas as pd

# "parameter"フォルダ内のすべてのExcelファイルとシートを読み取る関数
def load_parameters_from_directory(directory):
    resource_collections = {}
    for filename in os.listdir(directory):  # フォルダ内のファイルを順に処理
        if filename.endswith('.xlsx'):  # Excelファイルを判定
            file_path = os.path.join(directory, filename)
            workbook_name = os.path.splitext(filename)[0]  # ファイル名を拡張子なしで取得
            if workbook_name not in resource_collections:
                resource_collections[workbook_name] = []

            excel_data = pd.ExcelFile(file_path)
            for sheet_name in excel_data.sheet_names:  # Excelファイル内のすべてのシートを処理
                data = pd.read_excel(file_path, sheet_name=sheet_name)
                sheet_data = {}
                for _, row in data.iterrows():  # 各行のデータを処理
                    resource = row['resource']  # リソース名を取得
                    argument = row['arguments']  # 引数名を取得
                    value = row['value']  # 値を取得

                    # 数値の文字列表現を必要に応じて実際の数値型に変換
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            pass  # 数値に変換できない場合はそのまま文字列として扱う

                    # ネストされた引数を処理
                    keys = argument.split('.')  # ドットで区切られたキーを分割
                    current = sheet_data.setdefault(resource, {})
                    for key in keys[:-1]:  # 最後のキー以外でループ
                        if key.isdigit():  # 配列インデックスの場合
                            key = int(key)
                            if not isinstance(current, list):
                                current = []  # 現在のオブジェクトをリストに変換
                                sheet_data[resource] = current
                            while len(current) <= key:
                                current.append({})
                            current = current[key]
                        else:
                            if key not in current:
                                current[key] = {}
                            current = current[key]

                    last_key = keys[-1]
                    if last_key.isdigit():
                        last_key = int(last_key)
                        if not isinstance(current, list):
                            current = []
                            sheet_data[resource] = current
                        while len(current) <= last_key:
                            current.append({})
                        current[last_key] = value
                    else:
                        current[last_key] = value

                resource_collections[workbook_name].append({sheet_name: sheet_data})
    return resource_collections

# .tfvarsファイルの内容をフォーマットして生成
def generate_tfvars_content(resource_collections):
    lines = []
    for workbook_name, sheets in resource_collections.items():
        lines.append(f"{workbook_name} = [")
        for sheet_data in sheets:
            for sheet_name, resources in sheet_data.items():
                lines.append(f"  {{")
                for resource, arguments in resources.items():
                    lines.append(f"    {resource} = {{")
                    for key, value in arguments.items():  # 各引数を処理
                        if isinstance(value, dict):  # ネストされた引数の場合
                            lines.append(f"      {key} = {{")
                            for sub_key, sub_value in value.items():  # サブキーを処理
                                lines.append(f"        {sub_key} = \"{sub_value}\"")
                            lines.append("      }")
                        elif isinstance(value, list):  # 配列の場合
                            lines.append(f"      {key} = [")
                            for item in value:
                                lines.append(f"        {item},")
                            lines.append("      ]")
                        else:  # 単一の引数の場合
                            lines.append(f"      {key} = \"{value}\"")
                    lines.append("    }")
                lines.append("  },")
        lines.append("]")
    return "\n".join(lines)

# パラメータファイルを処理するメインスクリプト
def main():
    parameter_directory = './parameter'  # パラメータファイルを格納するディレクトリ
    output_directory = './output_tfvars'  # .tfvarsファイルを保存するディレクトリ

    if not os.path.exists(output_directory):  # 出力ディレクトリが存在しない場合は作成
        os.makedirs(output_directory)

    resource_collections = load_parameters_from_directory(parameter_directory)  # パラメータを読み取る
    tfvars_content = generate_tfvars_content(resource_collections)  # .tfvars内容を生成

    output_path = os.path.join(output_directory, 'output.tfvars')  # 出力ファイルのパス
    with open(output_path, 'w') as f:  # .tfvarsファイルを書き込む
        f.write(tfvars_content)

    print(f".tfvarsファイルが生成されました: {output_path}")

if __name__ == "__main__":
    main()
