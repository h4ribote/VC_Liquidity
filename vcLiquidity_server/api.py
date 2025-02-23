from fastapi import APIRouter, HTTPException, Request
from time import time
from discord_interactions import verify_key as webhook_verify
from webhook_class import WebhookPost
from pydantic import BaseModel
from typing import Literal
import swap_process
import config
router = APIRouter()

@router.post("/webhook")
async def Webhook_post(request: Request, webhook: WebhookPost):
    print(request.headers)
    request_signature = request.headers['X-Signature-Ed25519']
    request_timestamp = request.headers['X-Signature-Timestamp']
    body = await request.body()

    print(await request.json())

    if not webhook_verify(body, request_signature, request_timestamp, config.Discord.PUBLIC_KEY):
        raise HTTPException(401, "Bad request signature")

    timestamp_error = abs(time() - float(request_timestamp)) > 15
    
    if timestamp_error:
        raise HTTPException(401, f"Your watch is broken ({timestamp_error})")

    if webhook.type == 1: # PING
        return {"type":1} # PONG
    if webhook.data is None:
        return {"type":1}
    
    claim = webhook.data[0]

    if claim.metadata is None:
        return {"type":1}

    if not claim.status == 'approved':
        return {"type":1}
    
    swap_data = claim.metadata

    if swap_data.type == 'deposit':
        result_bool, reason = swap_process.add_liquidly(claim.payer.discord.id,swap_data.currency_unit,claim.currency.id,claim.amount)
        print(f"result_bool: {result_bool}, reason: {reason}")
        if result_bool:
            return {}
        else:
            return HTTPException(400, f"transaction failed: {reason}")
    else:
        result_bool, reason = swap_process.swap(claim.payer.discord.id,swap_data.type,swap_data.currency_unit,claim.currency.unit,claim.amount)
        print(f"result_bool: {result_bool}, reason: {reason}")
        if result_bool:
            return {}
        else:
            return HTTPException(400, f"Swap failed: {reason}")

class SwapInfo(BaseModel):
    reserve_base_currency:int
    reserve_pair_currency:int
    swap_fee:int

@router.get("/swap_info/{currency_unit}")
async def Swap_rate(currency_unit:str) -> SwapInfo:
    result_bool, result = swap_process.get_swap_info(currency_unit)
    if result_bool:
        return result
    else:
        raise HTTPException(400, result)

class SwapRequest(BaseModel):
    user_id:int
    input_amount:int

@router.post("/swap/buy/{currency_unit}")
async def Swap_buy(swap_request: SwapRequest, currency_unit:str):
    result_bool, result = swap_process.create_swap_claim(swap_request.user_id,currency_unit,'buy',swap_request.input_amount)
    if result_bool:
        return {"claim_id":result}
    else:
        raise HTTPException(400, result)

@router.post("/swap/sell/{currency_unit}")
async def Swap_sell(swap_request: SwapRequest, currency_unit:str):
    result_bool, result = swap_process.create_swap_claim(swap_request.user_id,currency_unit,'sell',swap_request.input_amount)
    if result_bool:
        return {"claim_id":result}
    else:
        raise HTTPException(400, result)
