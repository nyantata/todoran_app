import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# 列番号を指定して数値のみを取り出す関数を定義
def extract_numeric_by_column(df, column_number):
    column_name = df.columns[column_number]
    # 1行目に'%'が含まれているかどうかで、パーセント表示か判定
    if df[column_name].str.contains('%')[0]:
        parsent = True
    else:
        parsent = False
    # 正規表現を使って数値を検索
    df[column_name] = df[column_name].apply(lambda x: re.search(r'[-+]?\\d+(?:,\\d+)*(\\.\\d+)?', x))
    # 数値データをfloatとして適用
    df[column_name] = df[column_name].apply(lambda x: float(x.group().replace(',', '')) if x else None)
    # 整数の場合はintに変換
    df[column_name] = df[column_name].apply(lambda x: extract_numeric(x, parsent))

# 数値を抽出する関数を定義
def extract_numeric(value, parsent_flag):
    try:
        numeric_value = float(value)
        if parsent_flag:
            # %表記の場合は100で割った小数に変換
            return format(numeric_value / 100, '.4f')
        elif numeric_value.is_integer():
            # 値が整数の場合は整数に変換
            return int(numeric_value)
        else:
            # 値が小数の場合はそのまま
            return numeric_value
    except (ValueError, TypeError):
        # 数値以外の場合は None を返す
        return None

def main():
    st.title('とどらんデータ抽出Webアプリ')
    st.write('以下のURLを入力すると、対象ページのテーブルを抽出し、表示・CSV出力します。')

    # ユーザー入力
    url = st.text_input('URLを入力してください', 'https://todo-ran.com/t/kiji/16326')

    if st.button('抽出開始'):
        try:
            # データを取得
            response = requests.get(url)
            response.raise_for_status()

            # BeautifulSoupでパース
            soup = BeautifulSoup(response.text, 'html.parser')

            # タイトルを取得
            table_title = soup.find('div', {'class': 'kiji_title'})
            table_name = table_title.contents[0].contents[0] if table_title else '取得失敗'

            # テーブルを指定
            table = soup.find('div', {'id': 'kiji_table_swap'})
            if not table:
                st.error('テーブルが見つかりませんでした。URLを確認してください。')
                return

            # データフレームに変換
            df = pd.read_html(str(table))[0]

            # 列名の準備
            df_1 = df.columns.values
            columns_l = []

            # 列名を整える
            if len(df_1) == 5:
                # 5列の場合、総数と人口10万人あたりを分離
                for i in range(len(df_1)):
                    if df.columns.values[i][0] == df.columns.values[i][1]:
                        columns_l.append(df.columns.values[i][0])
                    else:
                        text1 = str(df.columns.values[i][0])
                        text2 = str(df.columns.values[i][1])
                        columns_l.append(text1 + '_' + text2)
            else:
                # それ以外の場合はそのまま
                for i in range(len(df_1)):
                    text1 = str(df.columns.values[i][0])
                    columns_l.append(text1)

            # スペースを除去
            columns_l = [re.sub(r'\\s', '', word) for word in columns_l]

            # 列名を適用
            df.columns = columns_l

            # 順位のデータ型をintにする
            df['順位'] = pd.to_numeric(df['順位'], errors='coerce')
            df['順位'] = df['順位'].fillna(0).astype(int)

            # 列番号を指定して数値のみを取り出す
            extract_numeric_by_column(df, 2)

            # もし3列目が偏差値でなければ数値抽出
            if df.columns[3] != '偏差値':
                extract_numeric_by_column(df, 3)

            # 47都道府県のデータを抜き出し
            output_df = df.iloc[0:47, :]
            filename = f'{table_name}.csv'

            st.subheader('テーブル名')
            st.write(table_name)

            st.subheader('抽出結果（上位47行）')
            st.dataframe(output_df)

            # CSV出力ボタン
            csv_data = output_df.to_csv(index=False)
            st.download_button(
                label='CSVファイルをダウンロード',
                data=csv_data,
                file_name=filename,
                mime='text/csv'
            )

        except requests.exceptions.RequestException as e:
            st.error(f'URLリクエストでエラーが発生しました: {e}')
        except Exception as e:
            st.error(f'エラーが発生しました: {e}')

if __name__ == '__main__':
    main()
