//
// Created by motawe on 5/19/26.
//

#ifndef FIRMWARE_MOTOR_H
#define FIRMWARE_MOTOR_H

#define KM_FF (0.05f)
#define TAU_FF (0.12f)
#define TS (0.005f)
#define FF_GAIN_POS (1.0f / KM_FF)
#define FF_GAIN_DER (TAU_FF / (KM_FF * TS))
#define KP (16.85f)
#define KI (430.0f)
#define U_MAX (24.0f)
#define U_MIN (-24.0f)

#include "PWM_expander.h"
#include "Encoder.h"
#include <cmath>


typedef struct {
	double kp,ki,kd;
}pid_constants;

class Motor {
	Encoder* _encoder;
	PWM_expander* _pwm;
	uint8_t _channel_a, _channel_b;
	pid_constants* _constants;

	public:
		Motor(Encoder* encoder, PWM_expander* pwm, uint8_t channel_a, uint8_t channel_b, pid_constants* constants);
		void set_pid_constants(pid_constants* constants);
		float apply_reference_filter(float raw_velocity_cmd);
		float compute_feedforward_control(float w_ref);
		float compute_pi_traditional(float error, bool system_is_saturated);
		void update_control(float cmd_vel);
		void update_pid(int16_t setpoint);
		void move(float speed);
		void stop();
		void smoothing(float speed);

		int16_t last_error;
		float max_speed = 1.4;
		float _smoothed_speed = 0;
		uint32_t last_time;
		int16_t _output = 0;
	private:
		float ref_u_prev = 0.0f;
		float ref_y_prev = 0.0f;
		float w_ref_prev = 0.0f;
		float pi_e_prev = 0.0f;
		float pi_u_prev = 0.0f;
		float pi_integral_sum = 0.0f;
};


#endif //FIRMWARE_MOTOR_H