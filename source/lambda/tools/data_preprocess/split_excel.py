
# pip install tabulate openpyxl pandas
import os
import glob
import openpyxl
import argparse
import pandas as pd

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_path', type=str, default='./excels', help='input path')
    parser.add_argument('--output_path', type=str, default='./output/excel_output', help='output path')
    args = parser.parse_args()
    input_path = args.input_path
    output_path = args.output_path

    # 打开Excel文件
    xlsx_files = glob.glob(os.path.join(input_path, '*.xlsx'))

    # 遍历每个 .xlsx 文件
    for xlsx_file in xlsx_files:
        xlsx_file_name = os.path.basename(xlsx_file)
        print(f"processing {xlsx_file_name}")
        try:
            workbook = openpyxl.load_workbook(xlsx_file)

            for worksheet in workbook.worksheets:

                df = pd.DataFrame(worksheet.values)
                df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)

                header = df.loc[0].values
                print(f"header: {header}")

                for i, row in df[1:].iterrows():
                    data = [ str(item).replace('\n', ';') for item in row.values]
                    row_df = pd.DataFrame([data], columns=header)
                    markdown_table = row_df.to_markdown(index=False)
                        
                    # 写入Markdown文件
                    filename = f"{output_path}/{xlsx_file_name}_{worksheet.title}_row_{i}.txt"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(markdown_table)

                    print(f'已将第{i}行数据写入文件 {filename}')
        except Exception as e:
            print(str(e))