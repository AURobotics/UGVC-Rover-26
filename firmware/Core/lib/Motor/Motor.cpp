//
// Created by motawe on 5/19/26.
//

#include "Motor.h"

Motor::Motor(Encoder* encoder, PWM_expander* pwm, uint8_t channel_a, uint8_t channel_b, pid_constants* constants) : _encoder(encoder), _pwm(pwm), _channel_a(channel_a), _channel_b(channel_b), _constants(constants) {}

void Motor::set_pid_constants(pid_constants* constants) {
    _constants = constants;
}

float Motor::apply_reference_filter(float raw_velocity_cmd) {
	float y_curr = (REF_FILT_B0 * raw_velocity_cmd) + (REF_FILT_B1 * ref_u_prev) - (REF_FILT_A1 * ref_y_prev);
	ref_u_prev = raw_velocity_cmd;
	ref_y_prev = y_curr;
	return y_curr;
 }

float Motor::compute_feedforward_control(float w_ref) {
	float ff_out = (FF_GAIN_POS * w_ref) + (FF_GAIN_DER * (w_ref - w_ref_prev));
	w_ref_prev = w_ref;
	return ff_out;
} // Returned raw, DO NOT CLAMP HERE

float Motor::compute_pi_traditional(float error, bool system_is_saturated) {
	float p_term = KP * error;
// Only accumulate integral if the combined system has headroom
	if (!system_is_saturated) {
		pi_integral_sum += (KI * TS * error);
	}
	return p_term + pi_integral_sum;
}

void Motor::update_control(float cmd_vel) {
	float raw_cmd_vel = _encoder->get_raw_velocity();
	float filtered_ref = apply_reference_filter(cmd_vel);
	float filtered_sensor = _encoder->get_velocity(raw_cmd_vel);


	float error = filtered_ref - filtered_sensor;
	float ff_effort = compute_feedforward_control(filtered_ref);
	float p_term_prediction = KP * error;
	float expected_total = ff_effort + p_term_prediction + pi_integral_sum;
	bool is_saturated = (expected_total >= U_MAX) || (expected_total <= U_MIN);
	float pi_effort = compute_pi_traditional(error, is_saturated);
	float total_effort = ff_effort + pi_effort;
	if (total_effort > U_MAX) total_effort = U_MAX;
	if (total_effort < U_MIN) total_effort = U_MIN;
	move((total_effort / 24.0) * max_speed);
}
/*
void Motor::update_pid(int16_t setpoint) {
    int16_t current = _encoder->get_velocity();
    int16_t error = setpoint - current;
    uint32_t dt = HAL_GetTick() - last_time;

    int16_t pout = _constants->kp * error;
    if (_output < 4095)
        _integral += error * dt;

    int16_t dout = _constants->kd * ((setpoint - current) - last_error)/dt;
    int16_t iout = _constants->ki * pi_integral_sum;
    _output = pout + dout + iout;

    if (_output > 4095)
        _output = 4095;
    else if (_output < -4095)
        _output = -4095;

    move(_output);
}
*/
void Motor::move(float speed) {
     if (speed >  max_speed) speed =  max_speed;
    if (speed < -max_speed) speed = -max_speed;

    if (speed < 0) {
        uint16_t pwm_value = (uint16_t)((-speed / max_speed) * 4095);
        _pwm->set_channel(_channel_b, pwm_value);
        _pwm->set_channel(_channel_a, 0);
    } else {
        uint16_t pwm_value = (uint16_t)((speed / max_speed) * 4095);
        _pwm->set_channel(_channel_a, pwm_value);
        _pwm->set_channel(_channel_b, 0);
    }
}

void Motor::stop() {
    _pwm->set_channel(_channel_a, 0);
    _pwm->set_channel(_channel_b, 0);
}

void Motor::smoothing(float speed) {
    _smoothed_speed = (0.2 * speed) + ((1.0f - 0.2) * _smoothed_speed);

    move(_smoothed_speed);
}