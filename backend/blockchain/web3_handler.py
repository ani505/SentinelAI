from typing import Optional
from web3 import Web3
from web3.exceptions import ContractLogicError


class Web3Handler:
    def __init__(self, rpc_url: str, contract_address: str, contract_abi: list, private_key: str):
        self._connected = False
        self.contract = None
        self.account = None
        self.w3 = None

        if not rpc_url or not private_key or not contract_address:
            print("[Web3] Missing config - running in local-only mode.", flush=True)
            return

        try:
            self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))

            if not self.w3.is_connected():
                print("[Web3] Can't reach RPC endpoint - local-only mode.", flush=True)
                return

            self.account = self.w3.eth.account.from_key(private_key)

            checksum_addr = Web3.to_checksum_address(contract_address)
            self.contract = self.w3.eth.contract(address=checksum_addr, abi=contract_abi)

            self._connected = True
            print(f"[Web3] Connected to Sepolia. Account: {self.account.address}", flush=True)

        except Exception as e:
            print(f"[Web3] Init failed ({e}) - local-only mode.", flush=True)

    def is_connected(self) -> bool:
        return self._connected

    def _hash_to_bytes32(self, hex_hash: str) -> bytes:
        clean = hex_hash.replace("0x", "")
        return bytes.fromhex(clean)

    def register_model(self, model_hash: str, model_name: str) -> str:
        """
        Writes the model hash to the smart contract.
        Returns the tx hash as a hex string.
        Raises RuntimeError if not connected.
        """
        if not self._connected:
            raise RuntimeError("Blockchain not connected")

        hash_bytes = self._hash_to_bytes32(model_hash)
        nonce = self.w3.eth.get_transaction_count(self.account.address)

        tx = self.contract.functions.registerModel(
            hash_bytes, model_name
        ).build_transaction({
            "from": self.account.address,
            "nonce": nonce,
            "gas": 120_000,
            "gasPrice": self.w3.eth.gas_price,
        })

        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

        # Wait for 1 block confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        if receipt.status != 1:
            raise RuntimeError(f"Transaction reverted: {tx_hash.hex()}")

        return tx_hash.hex()

    def verify_model(self, model_hash: str) -> bool:
        """Read-only check: is this hash registered on-chain? No gas needed."""
        if not self._connected:
            return False
        try:
            hash_bytes = self._hash_to_bytes32(model_hash)
            return self.contract.functions.isModelRegistered(hash_bytes).call()
        except Exception:
            return False
