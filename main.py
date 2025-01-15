import os
import pandas as pd
import json
from collections import defaultdict
import subprocess

def read_excel_files(folder_path):
    """
    指定されたフォルダ内のすべてのExcelファイルを読み込み、データフレームとして統合します。

    Args:
        folder_path (str): Excelファイルが保存されているフォルダのパス。

    Returns:
        pd.DataFrame: 統合されたデータフレーム。
    """
    data = []
    for file_name in os.listdir(folder_path):
        # .xlsx拡張子を持つファイルのみ処理
        if file_name.endswith(".xlsx"):
            file_path = os.path.join(folder_path, file_name)
            # ファイルを読み込み、リストに追加
            df = pd.read_excel(file_path)
            data.append(df)
    # すべてのデータフレームを結合して返す
    return pd.concat(data, ignore_index=True)

def parse_nested_key(resource_dict, keys, value):
    """
    ネストされたキーを再帰的に処理し、辞書やリスト構造を構築します。

    Args:
        resource_dict (dict): 対象となるリソース辞書。
        keys (list): 分解されたキーのリスト。
        value: 設定する値。
    """
    key = keys[0]

    if len(keys) == 1:
        # 最後のキーの場合、値を直接設定
        if key.isdigit():
            # 数値の場合はリストのインデックスとして処理
            index = int(key)
            if not isinstance(resource_dict, list):
                # リストに変換し初期化
                resource_dict[:] = [{} for _ in range(index + 1)]
            while len(resource_dict) <= index:
                resource_dict.append({})
            resource_dict[index] = value
        else:
            # 辞書として値を設定
            resource_dict[key] = value
        return

    # 中間キーを処理
    if key.isdigit():
        # 数値の場合はリストとして処理
        index = int(key)
        if not isinstance(resource_dict, list):
            resource_dict[:] = [{} for _ in range(index + 1)]
        while len(resource_dict) <= index:
            resource_dict.append({})
        # 再帰的に次のキーを処理
        parse_nested_key(resource_dict[index], keys[1:], value)
    else:
        # 辞書として中間キーを処理
        if key not in resource_dict or not isinstance(resource_dict[key], (dict, list)):
            # 次のキーが数値ならリスト、そうでなければ辞書を初期化
            resource_dict[key] = [] if keys[1].isdigit() else {}
        # 再帰的に次のキーを処理
        parse_nested_key(resource_dict[key], keys[1:], value)

def convert_to_hcl_with_proper_list_formatting(data):
    """
    データフレームをHCL形式に変換します。リスト内の辞書をHCL形式で整形。

    Args:
        data (pd.DataFrame): パラメータシートのデータ。

    Returns:
        str: HCL形式の文字列。
    """
    resources = defaultdict(dict)

    for _, row in data.iterrows():
        # generate_tfvars_flagがFalseの行はスキップ
        if not row['generate_tfvars_flag']:
            continue

        resource = row['resource']
        argument = row['arguments']
        value = row['value']

        # 値を適切な型（intまたはfloat）に変換
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass

        # リソースが未定義の場合は初期化
        if resource not in resources:
            resources[resource] = {}

        # argumentsをドットで分解してキーリストを取得
        keys = argument.split('.')
        # 再帰的にネストされた構造を構築
        parse_nested_key(resources[resource], keys, value)

    # HCL形式の出力
    def format_value_as_hcl(value):
        """
        値をHCL形式でフォーマットします。

        Args:
            value: フォーマット対象の値。

        Returns:
            str: HCL形式の文字列。
        """
        if isinstance(value, list):
            # リスト内がすべて辞書の場合、HCL形式で整形
            if all(isinstance(item, dict) for item in value):
                return "[\n" + ",\n".join(
                    "    {\n" + "\n".join(
                        f"      {k} = {json.dumps(v)}" for k, v in item.items()
                    ) + "\n    }" for item in value
                ) + "\n  ]"
            # その他のリストはJSON形式で出力
            return json.dumps(value)
        elif isinstance(value, dict):
            # 辞書を再帰的にフォーマット
            return "{\n" + "\n".join(
                f"    {k} = {format_value_as_hcl(v)}" for k, v in value.items()
            ) + "\n  }"
        else:
            # 単純な値をJSON形式で出力
            return json.dumps(value)

    # 各リソースをHCL形式で整形
    hcl_output = ""
    for resource, attributes in resources.items():
        hcl_output += f"{resource} = {{\n"
        for key, value in attributes.items():
            hcl_output += f"  {key} = {format_value_as_hcl(value)}\n"
        hcl_output += "}\n\n"
    return hcl_output

def debug_main_with_hcl_formatting(file_path):
    """
    デバッグ用HCL形式整形対応版メイン関数。

    Args:
        file_path (str): Excelファイルのパス。

    Returns:
        str: 出力されたHCLファイルのパス。
    """
    output_folder = './output_tfvars'
    output_file = os.path.join(output_folder, 'output.tfvars')

    # 出力フォルダが存在しない場合は作成
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Excelファイルを読み込み
    data = pd.read_excel(file_path)
    # HCL形式に変換
    hcl_output = convert_to_hcl_with_proper_list_formatting(data)

    # HCL形式をファイルに出力
    with open(output_file, 'w') as file:
        file.write(hcl_output)

    try:
        subprocess.run(['terraform', 'fmt', output_file], check=True)
        print(f"HCL形式の内容が{output_file}に出力され、フォーマットされました。")
    except subprocess.CalledProcessError as e:
        print(f"terraform fmtの実行中にエラーが発生しました: {e}")

    # 出力ファイルのパスを返す
    return output_file

# 実行例
if __name__ == "__main__":
    input_file_path = './parameter/ec2.xlsx'
    output_file = debug_main_with_hcl_formatting(input_file_path)
    print(f"HCLファイルが生成されました: {output_file}")
