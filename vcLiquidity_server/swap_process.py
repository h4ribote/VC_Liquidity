import pymysql.cursors
import config
from virtualcrypto import VirtualCryptoClient, Scope
from typing import Literal
from time import time

VCClient = VirtualCryptoClient(
    client_id=config.VirtualCrypto.client_id,
    client_secret=config.VirtualCrypto.client_secret,
    scopes=[Scope.Pay, Scope.Claim]
)

def dict_factory(cursor, row):
   d = {}
   for idx, col in enumerate(cursor.description):
       d[col[0]] = row[idx]
   return d

def DBConnection():
    MySQLConf = config.MySQL
    connection = pymysql.connect(host=MySQLConf.HOST,port=MySQLConf.PORT,
                                 user=MySQLConf.USER,password=MySQLConf.PASSWORD,database=MySQLConf.DATABASE,
                                 cursorclass=pymysql.cursors.DictCursor)
    cursor = connection.cursor()
    return connection, cursor

def insert_claim_history(claim_id:int, payer_id:int, currency_unit:str, amount:int, status:str) -> None:
    connection, cursor = DBConnection()
    cursor.execute("INSERT INTO claim_history (claim_id, status, currency_unit, amount, payer_id, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
                   (claim_id, status, currency_unit, amount, payer_id, int(time())))
    connection.commit()
    connection.close()

def get_swap_info(currency_unit:str) -> tuple[bool, dict]|tuple[bool, str]:
    connection, cursor = DBConnection()
    cursor.execute("SELECT * FROM liquidity WHERE pair_currency_unit = %s",(currency_unit,))
    pool_data = cursor.fetchall()
    connection.close()
    if not pool_data:
        return False, "Pool not found"
    pool_data = pool_data[0]
    pool_info = {'reserve_base_currency':pool_data['reserve_base_currency'],'reserve_pair_currency':pool_data['reserve_pair_currency'],'swap_fee':pool_data['swap_fee']}
    return True, pool_info

def create_swap_claim(user_id:int, pair_currency_unit:str, swap_type:Literal['buy','sell'], input_amount:int) -> tuple[bool, str|int]:
    try:
        connection, cursor = DBConnection()
        cursor.execute("SELECT * FROM liquidity WHERE pair_currency_unit = %s",(pair_currency_unit,))
        pool_data = cursor.fetchall()
        connection.close()
        if not pool_data:
            return False, "Pool not found"
        if swap_type == "buy":
            claim_id = VCClient.create_claim(user_id,config.Swap.base_currency_unit,input_amount,{"type":"buy","currency_unit":pair_currency_unit}).id
        else:
            claim_id = VCClient.create_claim(user_id,pair_currency_unit,input_amount,{"type":"sell","currency_unit":pair_currency_unit}).id
        return True, claim_id
    except Exception as e:
        print(e)
        return False, "Internal error"

def swap(user_id:int, swap_type:Literal['buy','sell'], pair_currency_unit:str, input_currency_unit:str, input_amount:int) -> tuple[bool, str|int]:
    if input_amount <= 0:
        return False, "Invalid input amount"
    if (swap_type == "buy" and not input_currency_unit == config.Swap.base_currency_unit) or (swap_type == "sell" and input_currency_unit == config.Swap.base_currency_unit):
        VCClient.create_user_transaction(input_currency_unit,user_id,input_amount)
        return False, "Invalid currency"
    connection, cursor = DBConnection()
    cursor.execute("SELECT * FROM liquidity WHERE pair_currency_unit = %s",(pair_currency_unit,))
    pool_data = cursor.fetchall()
    if not pool_data:
        connection.close()
        VCClient.create_user_transaction(input_currency_unit,user_id,input_amount)
        return False, "Pool not found"
    pool_data = pool_data[0]

    connection.begin()
    try:
        cursor.execute("SET @output_amount = 0")
        cursor.execute("CALL swap_currency(%s, %s, %s, @output_amount)",(swap_type, pair_currency_unit, input_amount))
        cursor.execute("SELECT @output_amount")
        output_amount = int(cursor.fetchall()[0]['@output_amount'])

        if output_amount == 0:
            connection.commit()
            connection.close()
            return True, output_amount
        elif swap_type == "buy":
            output_currency_unit = pair_currency_unit
        else:
            output_currency_unit = config.Swap.base_currency_unit

        VCClient.create_user_transaction(output_currency_unit,user_id,output_amount)
        connection.commit()
        connection.close()
        return True, output_amount
    except Exception as e:
        VCClient.create_user_transaction(input_currency_unit,user_id,input_amount)
        connection.rollback()
        connection.close()
        return False, str(e)

def add_liquidly(user_id:int, pair_currency_unit:str, input_currency_unit:str, input_amount:int) -> tuple[bool, str]:
    try:
        if input_amount <= 0:
            return False, "Invalid input amount"
        if input_amount < 500:
            VCClient.create_user_transaction(input_currency_unit,user_id,input_amount)
            return False, "Minimum deposit is 500"
        if pair_currency_unit == input_currency_unit or pair_currency_unit == config.Swap.base_currency_unit:
            VCClient.create_user_transaction(input_currency_unit,user_id,input_amount)
            return False, "Invalid currency"
        connection, cursor = DBConnection()
        cursor.execute("SELECT * FROM liquidity WHERE pair_currency_unit = %s",(pair_currency_unit,))
        pool_data = cursor.fetchall()
        connection.begin()
        if not pool_data:
            if input_currency_unit == config.Swap.base_currency_unit:
                connection.rollback()
                connection.close()
                VCClient.create_user_transaction(input_currency_unit,user_id,input_amount)
                return False, "Pool not found"
            pair_currency_circulation = VCClient.get_currency_by_unit(pair_currency_unit).total_amount
            if not pair_currency_circulation:
                connection.rollback()
                connection.close()
                VCClient.create_user_transaction(input_currency_unit,user_id,input_amount)
                return False, "Currency not found"
            if pair_currency_circulation // 2 > input_amount:
                connection.rollback()
                connection.close()
                VCClient.create_user_transaction(input_currency_unit,user_id,input_amount)
                return False, "Insufficient input amount (50% of circulation is required)"
            initial_base_reserve = config.Swap.initial_base_reserve
            cursor.execute("INSERT INTO liquidity (pair_currency_unit, reserve_pair_currency, reserve_base_currency, swap_fee) VALUES (%s, %s, %s, %s)",
                           (pair_currency_unit, input_amount, initial_base_reserve, 30))
            connection.commit()
            connection.close()
            return True, "Pool created"
        else:
            if input_currency_unit == config.Swap.base_currency_unit:
                cursor.execute("UPDATE liquidity SET reserve_base_currency = reserve_base_currency + %s WHERE pair_currency_unit = %s",
                               (input_amount, pair_currency_unit))
            else:
                cursor.execute("UPDATE liquidity SET reserve_pair_currency = reserve_pair_currency + %s WHERE pair_currency_unit = %s",
                               (input_amount, pair_currency_unit))
            connection.commit()
            connection.close()
            return True, "Liquidity added"
    except Exception as e:
        print(e)
        VCClient.create_user_transaction(input_currency_unit,user_id,input_amount)
        connection.rollback()
        connection.close()
        return False, "Unknown error"
