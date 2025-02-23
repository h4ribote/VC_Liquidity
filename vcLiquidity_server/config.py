class Swap:
    base_currency_name:str = "VC_Liquidity"
    base_currency_unit:str = "vcl"
    initial_base_reserve:int = 10_000_000

class MySQL:
    HOST:str = "localhost"
    PORT:int = 3306
    USER:str = ""
    PASSWORD:str = ""
    DATABASE:str = "vc_liquidity"

class VirtualCrypto:
    client_id:str = ""
    client_secret:str = ""
    public_key:str = ""
