"""
Blockchain service for crypto wallet integration.
Supports Ethereum, TRON, BSC via Moralis and TronGrid APIs.
"""
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime
from decimal import Decimal
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


class BlockchainService:
    """Service for blockchain wallet integration"""
    
    def __init__(self):
        self.moralis_api_key = os.getenv("MORALIS_API_KEY")
        self.moralis_base_url = "https://deep-index.moralis.io/api/v2.2"
        self.trongrid_base_url = "https://api.trongrid.io"
        
        if not self.moralis_api_key:
            logger.warning("MORALIS_API_KEY not set - blockchain features will be limited")
    
    def _moralis_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make request to Moralis API"""
        if not self.moralis_api_key:
            logger.error("Moralis API key not configured")
            return None
        
        url = f"{self.moralis_base_url}/{endpoint}"
        headers = {
            "X-API-Key": self.moralis_api_key,
            "accept": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Moralis API request failed: {e}")
            return None
    
    def _trongrid_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make request to TronGrid API"""
        url = f"{self.trongrid_base_url}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"TronGrid API request failed: {e}")
            return None
    
    def get_eth_balance(self, address: str) -> Optional[Dict]:
        """Get Ethereum wallet balance and tokens"""
        logger.info(f"Fetching ETH balance for {address}")
        
        # Get native ETH balance
        native_balance = self._moralis_request(f"{address}/balance", {"chain": "eth"})
        
        # Get ERC20 token balances
        tokens = self._moralis_request(f"{address}/erc20", {"chain": "eth"})
        
        if not native_balance:
            return None
        
        result = {
            "address": address,
            "network": "ethereum",
            "native_balance": Decimal(native_balance.get("balance", "0")) / Decimal(10**18),
            "native_currency": "ETH",
            "tokens": []
        }
        
        if tokens:
            for token in tokens:
                decimals = int(token.get("decimals", 18))
                balance = Decimal(token.get("balance", "0")) / Decimal(10**decimals)
                result["tokens"].append({
                    "symbol": token.get("symbol"),
                    "name": token.get("name"),
                    "balance": balance,
                    "contract": token.get("token_address")
                })
        
        return result
    
    def get_tron_balance(self, address: str) -> Optional[Dict]:
        """Get TRON wallet balance and TRC20 tokens"""
        logger.info(f"Fetching TRON balance for {address}")
        
        # Get account info
        account_info = self._trongrid_request(f"/v1/accounts/{address}")
        
        if not account_info or "data" not in account_info:
            return None
        
        account_data = account_info["data"][0] if account_info["data"] else {}
        
        # Native TRX balance (in SUN, 1 TRX = 1,000,000 SUN)
        trx_balance = Decimal(account_data.get("balance", 0)) / Decimal(1_000_000)
        
        result = {
            "address": address,
            "network": "tron",
            "native_balance": trx_balance,
            "native_currency": "TRX",
            "tokens": []
        }
        
        # Get TRC20 token balances
        trc20_data = account_data.get("trc20", {})
        if isinstance(trc20_data, dict):
            for token_address, token_info in trc20_data.items():
                # Get token details
                token_details = self._get_trc20_token_info(token_address)
                if token_details:
                    decimals = int(token_details.get("decimals", 6))
                    balance = Decimal(token_info) / Decimal(10**decimals)
                    result["tokens"].append({
                        "symbol": token_details.get("symbol"),
                        "name": token_details.get("name"),
                        "balance": balance,
                        "contract": token_address
                    })
        
        return result
    
    def _get_trc20_token_info(self, contract_address: str) -> Optional[Dict]:
        """Get TRC20 token information"""
        # Common TRC20 tokens
        known_tokens = {
            "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t": {"symbol": "USDT", "name": "Tether USD", "decimals": 6},
            "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8": {"symbol": "USDC", "name": "USD Coin", "decimals": 6},
        }
        
        if contract_address in known_tokens:
            return known_tokens[contract_address]
        
        # Try to fetch from API (implement if needed)
        return {"symbol": "UNKNOWN", "name": "Unknown Token", "decimals": 6}
    
    def get_eth_transactions(self, address: str, from_timestamp: Optional[int] = None) -> List[Dict]:
        """Get Ethereum transactions"""
        logger.info(f"Fetching ETH transactions for {address}")
        
        params = {"chain": "eth"}
        if from_timestamp:
            params["from_date"] = from_timestamp
        
        # Get native transactions
        native_txs = self._moralis_request(f"{address}", params)
        
        # Get ERC20 token transfers
        token_txs = self._moralis_request(f"{address}/erc20/transfers", params)
        
        transactions = []
        
        # Process native transactions
        if native_txs and "result" in native_txs:
            for tx in native_txs["result"]:
                transactions.append({
                    "hash": tx.get("hash"),
                    "from": tx.get("from_address"),
                    "to": tx.get("to_address"),
                    "value": Decimal(tx.get("value", "0")) / Decimal(10**18),
                    "currency": "ETH",
                    "timestamp": datetime.fromtimestamp(int(tx.get("block_timestamp", 0))),
                    "block": tx.get("block_number"),
                    "gas_used": tx.get("receipt_gas_used"),
                    "status": tx.get("receipt_status") == "1"
                })
        
        # Process token transfers
        if token_txs and "result" in token_txs:
            for tx in token_txs["result"]:
                decimals = int(tx.get("token_decimals", 18))
                transactions.append({
                    "hash": tx.get("transaction_hash"),
                    "from": tx.get("from_address"),
                    "to": tx.get("to_address"),
                    "value": Decimal(tx.get("value", "0")) / Decimal(10**decimals),
                    "currency": tx.get("token_symbol"),
                    "timestamp": datetime.fromisoformat(tx.get("block_timestamp").replace("Z", "+00:00")),
                    "block": tx.get("block_number"),
                    "token_address": tx.get("address"),
                    "status": True
                })
        
        return sorted(transactions, key=lambda x: x["timestamp"], reverse=True)
    
    def get_tron_transactions(self, address: str, from_timestamp: Optional[int] = None) -> List[Dict]:
        """Get TRON transactions"""
        logger.info(f"Fetching TRON transactions for {address}")
        
        params = {
            "limit": 200,
            "only_confirmed": True
        }
        if from_timestamp:
            params["min_timestamp"] = from_timestamp * 1000  # TronGrid uses milliseconds
        
        # Get TRX transactions
        trx_txs = self._trongrid_request(f"/v1/accounts/{address}/transactions", params)
        
        # Get TRC20 token transfers
        trc20_txs = self._trongrid_request(f"/v1/accounts/{address}/transactions/trc20", params)
        
        transactions = []
        
        # Process TRX transactions
        if trx_txs and "data" in trx_txs:
            for tx in trx_txs["data"]:
                raw_data = tx.get("raw_data", {})
                contract = raw_data.get("contract", [{}])[0]
                value = contract.get("parameter", {}).get("value", {})
                
                amount = Decimal(value.get("amount", 0)) / Decimal(1_000_000)
                
                transactions.append({
                    "hash": tx.get("txID"),
                    "from": value.get("owner_address"),
                    "to": value.get("to_address"),
                    "value": amount,
                    "currency": "TRX",
                    "timestamp": datetime.fromtimestamp(tx.get("block_timestamp", 0) / 1000),
                    "block": tx.get("blockNumber"),
                    "status": tx.get("ret", [{}])[0].get("contractRet") == "SUCCESS"
                })
        
        # Process TRC20 transfers
        if trc20_txs and "data" in trc20_txs:
            for tx in trc20_txs["data"]:
                token_info = tx.get("token_info", {})
                decimals = int(token_info.get("decimals", 6))
                amount = Decimal(tx.get("value", "0")) / Decimal(10**decimals)
                
                transactions.append({
                    "hash": tx.get("transaction_id"),
                    "from": tx.get("from"),
                    "to": tx.get("to"),
                    "value": amount,
                    "currency": token_info.get("symbol"),
                    "timestamp": datetime.fromtimestamp(tx.get("block_timestamp", 0) / 1000),
                    "block": tx.get("block"),
                    "token_address": tx.get("token_info", {}).get("address"),
                    "status": True
                })
        
        return sorted(transactions, key=lambda x: x["timestamp"], reverse=True)
    
    def detect_network(self, address: str) -> str:
        """Detect blockchain network from address format"""
        if address.startswith("0x") and len(address) >= 40:  # Allow 40-42 chars
            return "ethereum"  # Also works for BSC
        elif address.startswith("T") and len(address) == 34:
            return "tron"
        else:
            return "unknown"
    
    def get_wallet_balance(self, address: str) -> Optional[Dict]:
        """Get wallet balance (auto-detect network)"""
        network = self.detect_network(address)
        
        if network == "ethereum":
            return self.get_eth_balance(address)
        elif network == "tron":
            return self.get_tron_balance(address)
        else:
            logger.error(f"Unknown network for address: {address}")
            return None
    
    def get_wallet_transactions(self, address: str, from_timestamp: Optional[int] = None) -> List[Dict]:
        """Get wallet transactions (auto-detect network)"""
        network = self.detect_network(address)
        
        if network == "ethereum":
            return self.get_eth_transactions(address, from_timestamp)
        elif network == "tron":
            return self.get_tron_transactions(address, from_timestamp)
        else:
            logger.error(f"Unknown network for address: {address}")
            return []
