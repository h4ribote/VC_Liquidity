START TRANSACTION;

CREATE TABLE liquidity (
  `pair_currency_unit` VARCHAR(16) PRIMARY KEY,
  `reserve_base_currency` BIGINT UNSIGNED,
  `reserve_pair_currency` BIGINT UNSIGNED,
  `swap_fee` INT DEFAULT 30 -- 3%
);

CREATE TABLE swap_history (
  `swap_id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `pair_currency_unit` VARCHAR(16),
  `swap_type` VARCHAR(4),
  `input_amount` BIGINT UNSIGNED,
  `output_amount` BIGINT UNSIGNED,
  `timestamp` BIGINT UNSIGNED
);

CREATE TABLE claim_history (
  `claim_id` BIGINT UNSIGNED PRIMARY KEY,
  `status` VARCHAR(16),
  `currency_unit` VARCHAR(16),
  `amount` BIGINT UNSIGNED,
  `payer_id` BIGINT UNSIGNED,
  `timestamp` BIGINT UNSIGNED
);

DELIMITER //

CREATE PROCEDURE swap_currency(
  IN p_swap_type VARCHAR(4),
  IN p_pair_currency_unit VARCHAR(16),
  IN p_input_amount DECIMAL(32,0),
  OUT p_output_amount DECIMAL(32,0)
)
BEGIN
  DECLARE v_reserve_in DECIMAL(32,0);
  DECLARE v_reserve_out DECIMAL(32,0);
  DECLARE swap_timestamp BIGINT UNSIGNED;
  DECLARE v_fee INT;

  SELECT swap_fee INTO v_fee FROM liquidity WHERE pair_currency_unit = p_pair_currency_unit;
  
  SET swap_timestamp = UNIX_TIMESTAMP();

  IF p_swap_type = "buy" THEN
    SELECT reserve_base_currency, reserve_pair_currency INTO v_reserve_in, v_reserve_out
    FROM liquidity WHERE pair_currency_unit = p_pair_currency_unit;

    SET p_output_amount = FLOOR((v_reserve_out * (p_input_amount * (1000 - v_fee)) / 1000) / (v_reserve_in + (p_input_amount * (1000 - v_fee)) / 1000));

    UPDATE liquidity SET 
      reserve_base_currency = reserve_base_currency + p_input_amount, 
      reserve_pair_currency = reserve_pair_currency - p_output_amount 
    WHERE pair_currency_unit = p_pair_currency_unit;

  ELSEIF p_swap_type = "sell" THEN
    SELECT reserve_pair_currency, reserve_base_currency INTO v_reserve_in, v_reserve_out
    FROM liquidity WHERE pair_currency_unit = p_pair_currency_unit;

    SET p_output_amount = FLOOR((v_reserve_out * (p_input_amount * (1000 - v_fee)) / 1000) / (v_reserve_in + (p_input_amount * (1000 - v_fee)) / 1000));

    UPDATE liquidity SET 
      reserve_pair_currency = reserve_pair_currency + p_input_amount, 
      reserve_base_currency = reserve_base_currency - p_output_amount 
    WHERE pair_currency_unit = p_pair_currency_unit;
  ELSE
    SET p_output_amount = 0;
  END IF;


  INSERT INTO swap_history (pair_currency_unit, swap_type, input_amount, output_amount, timestamp)
    VALUES (p_pair_currency_unit, p_swap_type, p_input_amount, p_output_amount, swap_timestamp);
END //

DELIMITER ;

COMMIT;
