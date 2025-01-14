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

def process_excel_file(file_path):
    """Excelファイルを読み込み、tfvars形式に整形する"""
    tfvars_data = {}

    # Excelファイル内の全シートを処理
    with pd.ExcelFile(file_path) as xls:
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            # 必要な列が存在するか確認
            if not {"resource", "arguments", "value", "generate_tfvars_flag"}.issubset(df.columns):
                continue

            # フラグがTrueの行を抽出
            filtered_df = df[df["generate_tfvars_flag"] == True]

            # リソース名ごとにデータを整理
            for resource, group in filtered_df.groupby("resource"):
                resource_data = tfvars_data.setdefault(resource, {})
                for _, row in group.iterrows():
                    keys = row["arguments"].split(".")
                    value = row["value"]
                    current = resource_data

                    # 階層構造を構築
                    for key in keys[:-1]:
                        if key.isdigit():  # 配列インデックスの場合
                            key = int(key)
                        current = current.setdefault(key, {})
                    # 値を設定
                    final_key = keys[-1]
                    if final_key.isdigit():
                        final_key = int(final_key)
                    current[final_key] = value
    return tfvars_data

def save_tfvars(data):
    """tfvars形式でデータを保存し、terraform fmtを実行"""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    output_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)

    # 辞書をHCL形式に変換して保存
    with open(output_path, "w") as f:
        f.write(dict_to_hcl(data))

    # terraform fmtの実行
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
            file_path = os.path.join(INPUT_FOLDER, file_name)
            tfvars_data = process_excel_file(file_path)
            all_tfvars.update(tfvars_data)

    # tfvarsデータを保存
    save_tfvars(all_tfvars)

if __name__ == "__main__":
    main()
