from base64 import b64encode
from rsa import encrypt, PublicKey
from requests import Session, Response

class SteamUrl:
    API_URL = "https://api.steampowered.com"
    COMMUNITY_URL = "https://steamcommunity.com"
    STORE_URL = 'https://store.steampowered.com'
class CaptchaRequired(Exception):
    pass
class ApiException(Exception):
    pass

class WebSteam:
    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.one_time_code = ''
        self.session = Session()
        self.refresh_token = ''
        self.steam_id = None

    def _api_call(self, method: str, service: str, endpoint: str, version: str = 'v1', params: dict = None) -> Response:
        url = '/'.join([SteamUrl.API_URL, service, endpoint, version])
        headers = {
            "Referer": SteamUrl.COMMUNITY_URL + '/',
            "Origin": SteamUrl.COMMUNITY_URL
        }
        if method.upper() == 'GET':
            return self.session.get(url, params = params, headers = headers)
        elif method.upper() == 'POST':
            return self.session.post(url, data = params, headers = headers)
        else:
            raise ValueError('Method must be either GET or POST')

    def is_session_alive(self, session: Session = None):
        if not session:
            session = self.session
        main_page_response = session.get(SteamUrl.COMMUNITY_URL)
        return self.username.lower() in main_page_response.text.lower()

    def login(self, one_time_code: str) -> Session:
        self.one_time_code = one_time_code
        login_response = self._send_login_request()
        if not login_response.ok: return False
        login_response_json: dict = login_response.json()
        if not login_response_json.get('response'): return False
        self._check_for_captcha(login_response_json)
        self._update_steam_guard(login_response_json)
        finallized_response = self._finallize_login()
        if not finallized_response.ok: return False
        finallized_response_json: dict = finallized_response.json()
        if not finallized_response_json: return False
        self._perform_redirects(finallized_response_json)
        # self.set_sessionid_cookies()
        return self.session

    def _send_login_request(self) -> Response:
        rsa_params = self._fetch_rsa_params()
        encrypted_password = b64encode(encrypt(self.password.encode('utf-8'), rsa_params['rsa_key']))
        rsa_timestamp = rsa_params['rsa_timestamp']
        request_data = {'persistence': "1", 'encrypted_password': encrypted_password, 'account_name': self.username, 'encryption_timestamp': rsa_timestamp}
        return self._api_call('POST', 'IAuthenticationService', 'BeginAuthSessionViaCredentials', params = request_data)

    def set_sessionid_cookies(self):
        if not self.session or not self.session.cookies: return
        cookie_dict: dict = self.session.cookies.get_dict()
        if not cookie_dict: return
        for key in ['sessionid', 'steamRememberLogin', 'steamLoginSecure', 'steamRefresh_steam', 'steamCountry']:
            for domain in ['store.steampowered.com', 'help.steampowered.com', 'steamcommunity.com']:
                if not cookie_dict: continue
                cookie = cookie_dict.get(key, None)
                if cookie:
                    self.session.cookies.set(key, cookie, domain=domain, secure=True)

    def _fetch_rsa_params(self, current_number_of_repetitions: int = 0) -> dict:
        self.session.post(SteamUrl.COMMUNITY_URL)
        request_data = {'account_name': self.username}
        response = self._api_call('GET', 'IAuthenticationService', 'GetPasswordRSAPublicKey', params = request_data)
        if response.ok:
            response_json: dict = response.json()
            if response_json:
                key_data = response_json.get('response', {})
                publickey_mod = key_data.get('publickey_mod')
                publickey_exp = key_data.get('publickey_exp')
                timestamp = key_data.get('timestamp')
                if publickey_mod and publickey_exp and timestamp:
                    rsa_mod = int(publickey_mod, 16)
                    rsa_exp = int(publickey_exp, 16)
                    return {'rsa_key': PublicKey(rsa_mod, rsa_exp), 'rsa_timestamp': timestamp}

        maximal_number_of_repetitions = 5
        if current_number_of_repetitions < maximal_number_of_repetitions:
            return self._fetch_rsa_params(current_number_of_repetitions + 1)

        raise ApiException('Could not obtain rsa-key. Status code: %s' % response.status_code)

    @staticmethod
    def _check_for_captcha(login_response: dict) -> None:
        if login_response.get('captcha_needed', False):
            raise CaptchaRequired('Captcha required')

    def _perform_redirects(self, response_dict: dict) -> None:
        parameters = response_dict.get('transfer_info')
        if parameters is None:
            raise Exception('Cannot perform redirects after login, no parameters fetched')
        for pass_data in parameters:
            self.steam_id = response_dict.get('steamID')
            pass_data['params']['steamID'] = response_dict.get('steamID')
            self.session.post(pass_data['url'], pass_data['params'])

    def _update_steam_guard(self, login_response: dict) -> bool:
        client_id = login_response.get("response", {}).get("client_id")
        steamid = login_response.get("response", {}).get("steamid")
        request_id = login_response.get("response", {}).get("request_id")
        update_data = {
            'client_id': client_id,
            'steamid': steamid,
            'code_type': 3,
            'code': self.one_time_code
        }
        response = self._api_call('POST', 'IAuthenticationService', 'UpdateAuthSessionWithSteamGuardCode', params = update_data)
        if response.ok:
            self._pool_sessions_steam(client_id, request_id)
            return True
        else:
            raise Exception('Cannot update steam guard')

    def _pool_sessions_steam(self, client_id, request_id):
        pool_data = {
            'client_id': client_id,
            'request_id': request_id
        }
        response = self._api_call('POST', 'IAuthenticationService', 'PollAuthSessionStatus', params = pool_data)
        if not response.ok: return False
        response_json: dict = response.json()
        if not response_json: return False
        self.refresh_token = response_json.get('response', {}).get('refresh_token')

    def _finallize_login(self):
        sessionid = self.session.cookies.get("sessionid")
        redir = "https://steamcommunity.com/login/home/?goto="

        finallez_data = {
            'nonce': self.refresh_token,
            'sessionid': sessionid,
            'redir': redir
        }
        response = self.session.post("https://login.steampowered.com/jwt/finalizelogin", data = finallez_data)
        return response
