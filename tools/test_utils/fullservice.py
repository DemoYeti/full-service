# Copyright (c) 2022 MobileCoin, Inc.

# TODO: This should actually be more generic so that the python CLI 
#   can also use it as a library (or maybe tests will use the CLI's library)
import asyncio 
import http.client
import json
import os
import pathlib
import shutil
import subprocess
import time

from . import constants
from typing import Tuple
from urllib.parse import urlparse

class FullService:
    def __init__(self, remove_wallet_and_ledger=False):
        self.full_service_process = None
        self.account_map = None
        self.account_ids = None
        self.request_count = 0
        self.remove_wallet_and_ledger = remove_wallet_and_ledger
        
    def __enter__(self):
        self.remove_wallet_and_ledger = True
        self.start()
        return self
    
    def __exit__(self,exc_type, exc_val, exc_tb):
        self.stop()
        if self.remove_wallet_and_ledger:
            try:
                print(f"Removing ledger/wallet dbs")
                shutil.rmtree(self.wallet_path)
                shutil.rmtree(self.ledger_path)
            except Exception as e:
                print(e) 

    def stop(self):
        try:
            self.full_service_process.terminate()
        except subprocess.CalledProcessError as exc:
            if exc.returncode != 1:
                raise

    # return the result field of the request
    def _request(self, request_data):
        self.request_count += 1
        print('sending request to full service')
        url = 'http://127.0.0.1:9090/wallet'
        default_params = {
            "jsonrpc": "2.0",
            "api_version": "2",
            "id": self.request_count,
        }
        request_data = {**request_data, **default_params}

        print(f'request data: {request_data}')

        parsed_url = urlparse(url)
        connection = http.client.HTTPConnection(parsed_url.netloc)
        connection.request('POST', parsed_url.path, json.dumps(request_data), {'Content-Type': 'application/json'})
        r = connection.getresponse()

        try:
            raw_response = r.read()
            response_data = json.loads(raw_response)
            print(f'request returned {response_data}')
        except ValueError:
            raise ValueError('API returned invalid JSON:', raw_response)

        # TODO requests might be flakey due to timing issues... waiting 2 seconds to bypass most of these issues
        time.sleep(2)
        if 'error' in response_data:
            return response_data['error']
        else:
            return response_data['result']

    def import_account(self, mnemonic) -> bool:
        print(f'importing full service account {mnemonic}')
        params = {
            'mnemonic': mnemonic,
            'key_derivation_version': '2',
        }
        r = self._request({
            "method": "import_account",
            "params": params
        })

        if 'error' in r:
            # If we failed due to a unique constraint, it means the account already exists
            return 'Diesel Error: UNIQUE constraint failed' in r['error']['data']['details']
        return True

    # check if full service is synced within margin
    def sync_status(self, eps=5) -> bool:
        # ping network
        try:
            r = self._request({
                "method": "get_network_status"
            })
        except ConnectionError as e:
            print(e)
            return False

        # network offline
        if int(r['network_status']['network_block_height']) == 0:
            return False

        # network online
        network_block_height = int(r['network_status']['network_block_height'])
        local_block_height = int(r['network_status']['local_block_height'])

        # network is acceptably synced
        return (network_block_height - local_block_height < eps)

    # retrieve wallet status
    def get_wallet_status(self):
        r = self._request({
            "method": "get_wallet_status"
        })
        return r['wallet_status']

    # retrieve all accounts full service is aware of
    def get_all_accounts(self) -> Tuple[list, dict]:
        r = self._request({"method": "get_all_accounts"})
        print(r)
        return (r['account_ids'], r['account_map'])

    # retrieve information about account
    def get_account_status(self, account_id: str):
        params = {
            "account_id": account_id
        }
        r = self._request({
            "method": "get_account_status",
            "params": params
        })
        return r

    # build and submit a transaction from `account_id` to `to_address` for `amount` of pmob
    def send_transaction(self, account_id, to_address, amount):
        params = {
            "account_id": account_id,
            "addresses_and_values": [(to_address, amount)]
        }
        r = self._request({
            "method": "build_and_submit_transaction",
            "params": params,
        })
        print(r)
        return r['transaction_log']

    def sync_full_service_to_network(self, mc_network):
        network_synced = False
        count = 0
        attempt_limit = 100
        while network_synced is False and count < attempt_limit:
            count += 1
            network_synced = self.sync_status()
            if count % 10 == 0:
                print(f'attempt: {count}/{attempt_limit}')
            time.sleep(1)
        if count >= attempt_limit:
            raise Exception(f'Full service sync failed after {attempt_limit} attempts')
        print('Full service synced')
