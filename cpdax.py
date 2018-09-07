#!/usr/bin/env python
"""
@author: Songyang Guo
@contact: sit.songyang.guo@gmail.com
@file: Cpdax.py
@time: 08/27/2018
@document file: https://apidocs-eng.cpdax.com/reference
"""


import requests
import hmac
import hashlib
import base64
import time
import json


class Cpdax:

    domain_url = r"https://api.cpdax.com"
    api_url = r"https://api.cpdax.com/v1/"
    order_url = r"https://api.cpdax.com/v1/orders/"
    version = "v1"

    def __init__(self, api_key=None, api_secret=None):
        self.api_key = "" if api_key is None else api_key
        self.api_secret = "" if api_secret is None else api_secret

        self.private_method = True if (self.api_key and self.api_secret) else False

    def __sign(self, url_postfix, time_stamp, http_method="GET", params=None):
        url = "/" + self.version + "/" + url_postfix
        request_body = ""
        if params and http_method == "POST":
            request_body = self.json(params, {'convertArraysToObjects': True})
        data = self.api_key + str(time_stamp) + http_method + url + request_body
        return {"cmd": params, 'data': data, "method": http_method, "time": time_stamp, "url_postfix": url_postfix}

    def __get_header(self, signed_information):
        return {
            "CP-ACCESS-KEY": self.api_key,
            "CP-ACCESS-TIMESTAMP": signed_information["time"],
            "CP-ACCESS-DIGEST": self.hmac(self.encode(signed_information["data"]), self.encode(self.api_secret))
        }

    def __private_request(self, signed_information):
        url = self.api_url + signed_information["url_postfix"]
        header = self.__get_header(signed_information)

        if signed_information["method"] == "POST":
            response = requests.post(url, json=signed_information["cmd"], headers=header)
        else:
            if signed_information["cmd"]:
                response = requests.request(signed_information["method"], url, headers=header,
                                            params=signed_information["cmd"])
            else:
                response = requests.request(signed_information["method"], url, headers=header)

        return response

    def get_currencies(self):
        url = self.api_url + "currencies"
        response = requests.request("GET", url)
        return response.json()

    def get_products(self):
        url = self.api_url + "products"
        response = requests.request("GET", url)
        return response.json()

    def get_all_tickers(self):
        url = self.api_url + "tickers"
        response = requests.request("GET", url)
        return response.json()

    def get_all_tickers_detail(self):
        url = self.api_url + "tickers/detailed"
        response = requests.request("GET", url)
        return response.json()

    def get_tickers(self, ticker):
        url = self.api_url + "tickers/" + ticker
        response = requests.request("GET", url)
        return response.json()

    def get_tickers_detail(self, ticker):
        url = self.api_url + "tickers/" + ticker + "/detailed"
        response = requests.request("GET", url)
        return response.json()

    def get_recent_trading_list(self, ticker, start=None, end=None, limit=None):
        url = self.api_url + "trades/" + ticker

        querystring = {}
        if start:
            querystring["start"] = str(start)
        if end:
            querystring["end"] = str(end)
        if limit:
            querystring["limit"] = str(limit)

        response = requests.request("GET", url, params=querystring)
        return response.text

    def get_orderbook(self, ticker, limit=50):
        url = self.api_url + "orderbook/" + ticker
        querystring = {}

        if limit:
            querystring = {"limit": str(limit)}

        response = requests.request("GET", url, params=querystring)
        return response.json()

    def create_order(self, ticker, order_type, side, size=None, price=None, params={}):
        order_cmd = {
            "type": order_type,
            "side": side,
            "product_id": ticker,
        }

        if order_type == "limit":
            if price and size:
                order_cmd["price"] = price
                order_cmd["size"] = size
            else:
                raise ValueError("Price or Size parameter is missing for limit order")

        elif order_type == "market":
            if side == "buy":
                if params["funds"]:
                    order_cmd["fund"] = params["funds"]
                else:
                    raise ValueError("Funds parameter is missing for market buy order")
            elif side == "sell":
                if size:
                    order_cmd["size"] = size
                else:
                    raise ValueError("Size parameter is missing for market sell order")
            else:
                raise ValueError("side should be [buy|sell]")

        else:
            raise ValueError("order_type should be [limit|market]")

        utc_timestamp = str(int(time.time()))
        url_postfix = "orders"
        signature = self.__sign(url_postfix, utc_timestamp, http_method="POST", params=order_cmd)
        response = self.__private_request(signature)
        return response.json()

    def create_limit_order(self, symbol, *args):
        return self.create_order(symbol, 'limit', *args)

    def create_limit_buy_order(self, symbol, *args):
        return self.create_order(symbol, 'limit', 'buy', *args)

    def create_limit_sell_order(self, symbol, *args):
        return self.create_order(symbol, 'limit', 'sell', *args)

    def create_market_buy_order(self, symbol, size, funds):
        return self.create_order(symbol, 'market', 'buy', size, None, {"funds": funds})

    def create_market_sell_order(self, symbol, size):
        return self.create_order(symbol, 'market', 'sell', size, None)

    def fetch_all_orders(self, ticker, side=None, page=None, limit=None):
        utc_timestamp = str(int(time.time()))
        url_suffix = "orders/" + ticker

        querystring = {}
        if side:
            querystring["side"] = side
        if page:
            querystring["page"] = page
        if limit:
            querystring["limit"] = limit

        signature = self.__sign(url_suffix, utc_timestamp, http_method="GET", params=querystring)
        response = self.__private_request(signature)
        return response.text

    def fetch_order(self, ticker, order_id):
        utc_timestamp = str(int(time.time()))
        url_suffix = "orders/" + ticker + "/" + order_id
        signature = self.__sign(url_suffix, utc_timestamp, http_method="GET", params=None)
        response = self.__private_request(signature)
        return response.text

    def cancel_order(self, ticker, order_id):
        utc_timestamp = str(int(time.time()))
        url_suffix = "orders/" + ticker + "/" + order_id
        signature = self.__sign(url_suffix, utc_timestamp, http_method="DELETE", params=None)
        response = self.__private_request(signature)
        return response.text

    def cancel_all_orders(self, ticker, side=None):
        utc_timestamp = str(int(time.time()))
        url_suffix = "orders/" + ticker

        querystring = {}
        if side:
            querystring["side"] = side

        signature = self.__sign(url_suffix, utc_timestamp, http_method="DELETE", params=querystring)
        response = self.__private_request(signature)
        return response.text

    def fetch_fee_rates(self):
        # todo: still not functional
        utc_timestamp = str(int(time.time()))
        url_suffix = "fee-rates"
        signature = self.__sign(url_suffix, utc_timestamp, http_method="GET")
        response = self.__private_request(signature)
        return response.text

    def fetch_balance(self):
        utc_timestamp = str(int(time.time()))
        url_suffix = "balance"
        signature = self.__sign(url_suffix, utc_timestamp, http_method="GET")
        response = self.__private_request(signature)
        return response.json()

    @staticmethod
    def hmac(request, secret, algorithm=hashlib.sha256, digest="hex"):
        h = hmac.new(secret, request, algorithm)
        if digest == 'hex':
            return h.hexdigest()
        elif digest == 'base64':
            return base64.b64encode(h.digest())
        return h.digest()

    @staticmethod
    def json(data, params=None):
        return json.dumps(data, separators=(",", ":"))

    @staticmethod
    def encode(string):
        return string.encode()


def main():
    api_key = ""
    api_secret = ""

    test_conn = Cpdax(api_key, api_secret)

    # Public API function
    # print(test_conn.get_currencies())
    # print(test_conn.get_products())
    # print(test_conn.get_tickers("ETH-BTC"))
    # print(test_conn.get_tickers_detail("ETH-BTC"))
    # print(test_conn.get_all_tickers())
    # print(test_conn.get_all_tickers_detail())
    # print(test_conn.get_recent_trading_list("ETH-BTC"))
    # print(test_conn.get_orderbook("ETH-BTC", limit=50))

    # Create order
    # print(test_conn.create_order("ETH-BTC", "limit", "buy", 1000, 0.05094476))
    # print(test_conn.create_limit_order("ETH-BTC", "buy", 0.00261507, 0.0372132))
    # print(test_conn.create_limit_buy_order("ETH-BTC", 0.00261507, 0.0372132))
    # print(test_conn.create_limit_sell_order("ETH-BTC", 0.11914155, 0.04544666))

    # Fetch orders
    # print(test_conn.fetch_all_orders("ETH-BTC", limit= 10, side="sell"))
    # print(test_conn.fetch_order("ETH-BTC", "755c1721-c032-4315-ac44-02d032458414"))

    # Cancel orders
    # print(test_conn.cancel_order("ETH-BTC", "755c1721-c032-4315-ac44-02d032458414"))
    # print(test_conn.cancel_all_orders("ETH-BTC", side='sell'))

    # Fetch Balance and fee rates
    # print(test_conn.fetch_balance())
    # print(test_conn.fetch_fee_rates())


if __name__ == "__main__":
    main()
