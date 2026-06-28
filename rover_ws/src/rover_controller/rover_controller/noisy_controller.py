#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.constants import S_TO_NS
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
import numpy as np
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped
import math
from tf_transformations import quaternion_from_euler

class NoisyController(Node):

    def __init__(self):
        super().__init__("noisy_controller")

        self.declare_parameter("wheel_radius", 0.033)
        self.declare_parameter("wheel_separation", 0.297)

        self.wheel_radius_     = self.get_parameter("wheel_radius").get_parameter_value().double_value
        self.wheel_separation_ = self.get_parameter("wheel_separation").get_parameter_value().double_value

        self.get_logger().info("Using wheel radius %f"     % self.wheel_radius_)
        self.get_logger().info("Using wheel separation %f" % self.wheel_separation_)

        self.left_wheel_prev_pos_  = 0.0
        self.right_wheel_prev_pos_ = 0.0
        self.x_                    = 0.0
        self.y_                    = 0.0
        self.theta_                = 0.0
        self.prev_time_            = None   # initialised from first sim-time stamp
        self.left_joint_idx_       = None
        self.right_joint_idx_      = None

        self.speed_conversion_ = np.array([
            [ self.wheel_radius_ / 2,                        self.wheel_radius_ / 2                       ],
            [ self.wheel_radius_ / self.wheel_separation_,  -self.wheel_radius_ / self.wheel_separation_  ]
        ])
        self.get_logger().info("Speed conversion matrix:\n%s" % self.speed_conversion_)

        self.joint_sub_ = self.create_subscription(
            JointState, "joint_states", self.jointCallback, 10
        )
        self.odom_pub_ = self.create_publisher(
            Odometry, "diff_drive_controller/odom_noisy", 10
        )

        # ── Odometry message ────────────────────────────────────────────────────
        # child_frame_id = base_footprint_ekf so robot_localization can resolve
        # the transform and process this message correctly.
        self.odom_msg_                         = Odometry()
        self.odom_msg_.header.frame_id         = "odom"
        self.odom_msg_.child_frame_id          = "base_footprint_ekf"
        self.odom_msg_.pose.pose.orientation.x = 0.0
        self.odom_msg_.pose.pose.orientation.y = 0.0
        self.odom_msg_.pose.pose.orientation.z = 0.0
        self.odom_msg_.pose.pose.orientation.w = 1.0

        # ── TF broadcast ────────────────────────────────────────────────────────
        # Kept as base_footprint_noisy so it appears separately in RViz.
        self.br_                              = TransformBroadcaster(self)
        self.transform_stamped_               = TransformStamped()
        self.transform_stamped_.header.frame_id = "odom"
        self.transform_stamped_.child_frame_id  = "base_footprint_noisy"


    def jointCallback(self, msg: JointState):

        # Resolve joint indices once
        if self.left_joint_idx_ is None or self.right_joint_idx_ is None:
            try:
                self.left_joint_idx_  = msg.name.index("left_wheel_joint")
                self.right_joint_idx_ = msg.name.index("right_wheel_joint")
            except ValueError:
                self.get_logger().warn(
                    "Waiting for wheel joints…", throttle_duration_sec=2.0
                )
                return

        current_time = Time.from_msg(msg.header.stamp)

        # Seed state from the very first sim-time message
        if self.prev_time_ is None:
            self.prev_time_           = current_time
            self.left_wheel_prev_pos_ = msg.position[self.left_joint_idx_]
            self.right_wheel_prev_pos_= msg.position[self.right_joint_idx_]
            return

        dt = (current_time - self.prev_time_).nanoseconds / S_TO_NS
        if dt <= 0.0:
            return

        # ── Noisy encoder readings ───────────────────────────────────────────
        wheel_encoder_left  = msg.position[self.left_joint_idx_]  + np.random.normal(0, 0.005)
        wheel_encoder_right = msg.position[self.right_joint_idx_] + np.random.normal(0, 0.005)

        dp_left  = wheel_encoder_left  - self.left_wheel_prev_pos_
        dp_right = wheel_encoder_right - self.right_wheel_prev_pos_

        # Store true positions to avoid noise accumulation in prev state
        self.left_wheel_prev_pos_  = msg.position[self.left_joint_idx_]
        self.right_wheel_prev_pos_ = msg.position[self.right_joint_idx_]
        self.prev_time_            = current_time

        # ── Kinematics via conversion matrix ────────────────────────────────
        fi_left  = dp_left  / dt
        fi_right = dp_right / dt

        vel       = self.speed_conversion_ @ np.array([fi_right, fi_left])
        linear    = vel[0]
        angular   = vel[1]

        d_s     = (self.wheel_radius_ * dp_right + self.wheel_radius_ * dp_left) / 2
        d_theta = (self.wheel_radius_ * dp_right - self.wheel_radius_ * dp_left) / self.wheel_separation_

        self.theta_ += d_theta
        self.x_     += d_s * math.cos(self.theta_)
        self.y_     += d_s * math.sin(self.theta_)

        q        = quaternion_from_euler(0, 0, self.theta_)
        msg_time = current_time.to_msg()

        # ── Publish odometry ─────────────────────────────────────────────────
        self.odom_msg_.header.stamp            = msg_time
        self.odom_msg_.pose.pose.position.x    = self.x_
        self.odom_msg_.pose.pose.position.y    = self.y_
        self.odom_msg_.pose.pose.orientation.x = q[0]
        self.odom_msg_.pose.pose.orientation.y = q[1]
        self.odom_msg_.pose.pose.orientation.z = q[2]
        self.odom_msg_.pose.pose.orientation.w = q[3]

        self.odom_msg_.pose.covariance[0]  = 0.01   # x
        self.odom_msg_.pose.covariance[7]  = 0.01   # y
        self.odom_msg_.pose.covariance[35] = 0.01   # yaw

        self.odom_msg_.twist.twist.linear.x  = linear
        self.odom_msg_.twist.twist.angular.z = angular

        self.odom_msg_.twist.covariance[0]  = 0.01   # vx
        self.odom_msg_.twist.covariance[7]  = 0.01   # vy
        self.odom_msg_.twist.covariance[35] = 0.01   # vyaw

        self.odom_pub_.publish(self.odom_msg_)

        # ── Broadcast TF (odom → base_footprint_noisy) ──────────────────────
        self.transform_stamped_.header.stamp                = msg_time
        self.transform_stamped_.transform.translation.x    = self.x_
        self.transform_stamped_.transform.translation.y    = self.y_
        self.transform_stamped_.transform.translation.z    = 0.0
        self.transform_stamped_.transform.rotation.x       = q[0]
        self.transform_stamped_.transform.rotation.y       = q[1]
        self.transform_stamped_.transform.rotation.z       = q[2]
        self.transform_stamped_.transform.rotation.w       = q[3]
        self.br_.sendTransform(self.transform_stamped_)


def main():
    rclpy.init()
    noisy_controller = NoisyController()
    rclpy.spin(noisy_controller)
    noisy_controller.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()