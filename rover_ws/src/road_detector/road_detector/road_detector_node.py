#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy

from sensor_msgs.msg import Image, PointCloud2, CameraInfo
from std_msgs.msg import Header, String

import numpy as np
from cv_bridge import CvBridge, CvBridgeError

# For point cloud conversion
from sensor_msgs_py import point_cloud2

# Import your custom modules
from .cv_code.road_features_detector import RoadFeatureDetector
from .cv_code.pipeline import RoadFeatureBEVPipeline


class RoadDetectorNode(Node):
    """ROS2 node for detecting road features (lane markings and potholes) from camera images"""
    
    def __init__(self):
        super().__init__('road_detector')
        
        # Initialize bridge
        self.bridge = CvBridge()
        
        # Declare parameters
        self._declare_parameters()
        
        # Get parameters
        self._load_parameters()
        
        # Validate parameters
        if not self._validate_parameters():
            self.get_logger().error("Parameter validation failed - node will not function correctly")
        
        # Initialize state variables
        self.pipeline = None
        self.image_size = (1920, 1080)  # Will be updated from first frame
        self.latest_image = None
        
        # Performance tracking
        self.processing_times = []
        self.frame_count = 0
        
        # Setup publishers, subscribers, and timers
        self.setup_comms()
        
        # Add dynamic parameter callback
        self.add_on_set_parameters_callback(self.parameters_callback)
        
        self.get_logger().info("Road Detector Node Initialized Successfully")
        self.get_logger().info(f"Debug images: {self.publish_debug_images}")
    
    def _declare_parameters(self):
        """Declare all node parameters with default values"""
        
        # Topic parameters
        self.declare_parameter('camera_topic', '/camera/image_raw')
        self.declare_parameter('camera_info_topic', '/camera/camera_info')
        self.declare_parameter('output_pointcloud_topic', '/road_detector/pointcloud')
        self.declare_parameter('output_lane_mask_topic', '/road_detector/debug/lane_mask')
        self.declare_parameter('output_bev_topic', '/road_detector/debug/bev_image')
        self.declare_parameter('output_stats_topic', '/road_detector/stats')
        
        # Camera parameters (extrinsic)
        self.declare_parameter('camera_height', 1.43)
        self.declare_parameter('pitch_deg', -50.0)
        self.declare_parameter('yaw_deg', 0.0)
        self.declare_parameter('roll_deg', 0.0)
        
        # Camera parameters (intrinsic)
        self.declare_parameter('fx', 1000.0)
        self.declare_parameter('fy', 1000.0)
        self.declare_parameter('cx', 960.0)
        self.declare_parameter('cy', 540.0)
        self.declare_parameter('dist_coeffs', [0.0, 0.0, 0.0, 0.0, 0.0])  # Assuming no distortion by default
        
        # Detection parameters
        self.declare_parameter('min_radius', 10)
        self.declare_parameter('max_radius', 200)
                
        # Debug parameters
        self.declare_parameter('publish_debug_images', False)
        self.declare_parameter('publish_performance_stats', False)
        
        # Point cloud parameters
        self.declare_parameter('max_points_per_cloud', 10000)
            
    def _load_parameters(self):
        """Load all parameters from the parameter server"""
        
        # Topic parameters
        self.camera_topic = self.get_parameter('camera_topic').value
        self.camera_info_topic = self.get_parameter('camera_info_topic').value
        self.pc_topic = self.get_parameter('output_pointcloud_topic').value
        self.lane_mask_topic = self.get_parameter('output_lane_mask_topic').value
        self.bev_topic = self.get_parameter('output_bev_topic').value
        self.stats_topic = self.get_parameter('output_stats_topic').value
        
        # Camera parameters
        self.camera_height = self.get_parameter('camera_height').value
        self.pitch_deg = self.get_parameter('pitch_deg').value
        self.yaw_deg = self.get_parameter('yaw_deg').value
        self.roll_deg = self.get_parameter('roll_deg').value

        # Camera intrinsic matrix
        fx = self.get_parameter('fx').value
        fy = self.get_parameter('fy').value
        cx = self.get_parameter('cx').value
        cy = self.get_parameter('cy').value
        self.dist_coeffs = self.get_parameter('dist_coeffs').value
        self.K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float64)
        
        # Detection parameters
        self.min_radius = self.get_parameter('min_radius').value
        self.max_radius = self.get_parameter('max_radius').value
                
        # Debug parameters
        self.publish_debug_images = self.get_parameter('publish_debug_images').value
        self.publish_performance_stats = self.get_parameter('publish_performance_stats').value
        
        # Point cloud parameters
        self.max_points_per_cloud = self.get_parameter('max_points_per_cloud').value
                
        self.consecutive_error_counter = 0
    
    def _validate_parameters(self):
        """Validate critical parameters and log warnings/errors"""
        valid = True
        
        # Camera height validation
        if self.camera_height <= 0:
            self.get_logger().error(f"Camera height must be positive! Current: {self.camera_height}")
            valid = False
        
        # Pitch validation
        if self.pitch_deg > 0:
            self.get_logger().warn(f"Positive pitch ({self.pitch_deg}°) means camera is pointing up - road detection may fail")
        
        # Focal length validation
        if self.get_parameter('fx').value <= 0 or self.get_parameter('fy').value <= 0:
            self.get_logger().error("Focal length (fx, fy) must be positive!")
            valid = False
                
        # Radius validation
        if self.min_radius >= self.max_radius:
            self.get_logger().error(f"min_radius ({self.min_radius}) must be less than max_radius ({self.max_radius})")
            valid = False
        
        return valid
    
    def setup_comms(self):
        """Setup publishers, subscribers, and timers"""
        
        # QoS profiles
        image_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        reliable_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Subscriber for camera images (BEST_EFFORT for real-time video)
        self.sub = self.create_subscription(
            Image, 
            self.camera_topic, 
            self.image_callback, 
            image_qos
        )
        
        # Publishers
        self.pc_pub = self.create_publisher(
            PointCloud2, 
            self.pc_topic, 
            reliable_qos
        )
        
        if self.publish_debug_images:
            self.img_pub = self.create_publisher(
                Image, 
                self.lane_mask_topic, 
                reliable_qos
            )
            
            self.bev_pub = self.create_publisher(
                Image, 
                self.bev_topic, 
                reliable_qos
            )
        
        if self.publish_performance_stats:
            self.stats_pub = self.create_publisher(
                String,
                self.stats_topic,
                reliable_qos
            )
    
    def initialize_pipeline(self, image_width, image_height):
        """Initialize the pipeline with correct image dimensions"""
        if self.pipeline is None:
            self.get_logger().info(f"Initializing pipeline with image size: {image_width}x{image_height}")
            
            # Create road detector and pipeline
            self.pipeline = RoadFeatureBEVPipeline(
                K=self.K,
                camera_height=self.camera_height,
                pitch_deg=self.pitch_deg,
                yaw_deg=self.yaw_deg,
                roll_deg=self.roll_deg,
                dist_coeffs=np.array(self.dist_coeffs, dtype=np.float64),  # shape (5,)
                image_size=(image_width, image_height),
                min_radius=self.min_radius,
                max_radius=self.max_radius
            )
            
            self.image_size = (image_width, image_height)
            self.get_logger().info("Pipeline initialization complete")
    
    def image_callback(self, msg):
        self._process_image(msg)
    
    def process_latest_image(self):
        """Process the latest image at controlled rate"""
        if self.latest_image is None:
            return
        
        msg = self.latest_image
        self.latest_image = None  # Clear after taking
        
        self._process_image(msg)
    
    def _process_image(self, msg):
        """Process a single image frame"""
        start_time = self.get_clock().now()
        
        try:
            # Convert ROS Image to OpenCV
            try:
                frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            except CvBridgeError as e:
                self.get_logger().error(f"CV Bridge error: {e}")
                return
            
            if frame is None or frame.size == 0:
                self.get_logger().warn("Empty frame received")
                return
            
            h, w = frame.shape[:2]
            
            # Initialize pipeline if not done yet
            if self.pipeline is None:
                self.initialize_pipeline(w, h)
            
            # Process frame through pipeline
            try:
                output, bev_image, lane_mask, lane_points, ground_circles, circle_clouds = \
                    self.pipeline.process_frame(frame)
            except Exception as e:
                self.get_logger().error(f"Pipeline processing error: {e}")
                self.consecutive_error_counter += 1
                return
            
            self.consecutive_error_counter = 0  # Reset error counter on success
            
            # Publish lane points as point cloud
            # Limit points to avoid large messages
            if len(lane_points) > self.max_points_per_cloud:
                lane_points = lane_points[:self.max_points_per_cloud]
            
            pc_msg = self.create_pointcloud2(lane_points, msg)
            self.pc_pub.publish(pc_msg)
            self.get_logger().debug(f"Published {len(lane_points)} lane points")
            
            # Publish circle point clouds
            for i, cloud in enumerate(circle_clouds):
                if len(cloud) > 0:
                    # Limit points
                    if len(cloud) > self.max_points_per_cloud:
                        cloud = cloud[:self.max_points_per_cloud]
                    
                    pc_msg = self.create_pointcloud2(cloud, msg)
                    self.pc_pub.publish(pc_msg)
                    self.get_logger().debug(f"Published circle cloud {i} with {len(cloud)} points")
            
            # Publish debug images
            if self.publish_debug_images:
                if lane_mask is not None:
                    try:
                        output_msg = self.bridge.cv2_to_imgmsg(lane_mask, "passthrough")
                        output_msg.header = msg.header
                        self.img_pub.publish(output_msg)
                    except CvBridgeError as e:
                        self.get_logger().error(f"CV Bridge error for lane_mask (shape={lane_mask.shape}, dtype={lane_mask.dtype}): {e}")
                else:
                    self.get_logger().warn("Lane mask is None, skipping debug image publish")

                if bev_image is not None:
                    try:
                        bev_msg = self.bridge.cv2_to_imgmsg(bev_image, "passthrough")
                        bev_msg.header = msg.header
                        self.bev_pub.publish(bev_msg)
                    except CvBridgeError as e:
                        self.get_logger().error(f"CV Bridge error for bev_image (shape={bev_image.shape}, dtype={bev_image.dtype}): {e}")
                else:
                    self.get_logger().warn("BEV image is None, skipping BEV debug image publish")
            
            # Performance statistics
            if self.publish_performance_stats:
                end_time = self.get_clock().now()
                processing_ms = (end_time - start_time).nanoseconds / 1e6
                self.update_performance_stats(processing_ms)
            
            self.frame_count += 1
            if self.frame_count % 100 == 0:
                self.get_logger().info(f"Processed {self.frame_count} frames successfully")
            
        except Exception as e:
            self.get_logger().error(f"Unexpected error processing frame: {str(e)}", throttle_duration_sec=5.0)
    
    def update_performance_stats(self, processing_ms):
        """Update and publish performance statistics"""
        self.processing_times.append(processing_ms)
        
        # Keep last 30 measurements
        if len(self.processing_times) > 30:
            self.processing_times.pop(0)
        
        # Calculate statistics
        avg_time = np.mean(self.processing_times)
        std_time = np.std(self.processing_times)
        fps = 1000.0 / avg_time if avg_time > 0 else 0
        
        # Create stats message
        stats_msg = String()
        stats_msg.data = (f"Frame: {self.frame_count}, "
                         f"Processing: {processing_ms:.2f}ms, "
                         f"Avg: {avg_time:.2f}ms ± {std_time:.2f}ms, "
                         f"FPS: {fps:.1f}")
        
        self.stats_pub.publish(stats_msg)
        
        # Log occasionally
        if self.frame_count % 100 == 0:
            self.get_logger().info(stats_msg.data)
    
    def create_pointcloud2(self, points, msg) -> PointCloud2:
        """Convert numpy array of points to PointCloud2 message"""
        header = Header()
        header.stamp = msg.header.stamp
        header.frame_id = msg.header.frame_id
        
        if len(points) == 0:
            # Return empty point cloud
            return point_cloud2.create_cloud_xyz32(header, np.zeros((0, 3)))
        
        # Ensure points are float32 for PointCloud2
        points_float32 = points.astype(np.float32)
        
        # Filter out invalid points (NaN or Inf)
        mask = np.isfinite(points_float32).all(axis=1)
        points_float32 = points_float32[mask]
        
        if len(points_float32) == 0:
            return point_cloud2.create_cloud_xyz32(header, np.zeros((0, 3)))
        
        # Swap x and y, and set z to -height (or modify as needed)
        # these transformations is to make the coordinates relative to the camera stamp
        modified_points = np.zeros_like(points_float32)
        modified_points[:, 0] = points_float32[:, 1]  # x becomes original y
        modified_points[:, 1] = points_float32[:, 0]  # y becomes original x
        modified_points[:, 2] = -self.camera_height  # set z to -camera_height (change this as needed)
        
        return point_cloud2.create_cloud_xyz32(header, modified_points)
    
    def parameters_callback(self, params):
        """Handle dynamic parameter updates"""
        result = rclpy.node.SetParametersResult(successful=True)
        
        for param in params:                       
            if param.name == 'publish_debug_images':
                self.publish_debug_images = param.value
                self.get_logger().info(f"Updated publish_debug_images to {self.publish_debug_images}")
            
            elif param.name == 'publish_performance_stats':
                self.publish_performance_stats = param.value
                self.get_logger().info(f"Updated publish_performance_stats to {self.publish_performance_stats}")
            
            elif param.name == 'max_points_per_cloud':
                self.max_points_per_cloud = param.value
                self.get_logger().info(f"Updated max_points_per_cloud to {self.max_points_per_cloud}")

            elif param.name == 'camera_height' and self.pipeline is not None:
                self.pipeline.set_camera_height(param.value)
                self.get_logger().info(f"Updated camera_height to {self.camera_height}")
            
            elif param.name == 'pitch_deg' and self.pipeline is not None:
                self.pipeline.set_pitch_deg(param.value)
                self.get_logger().info(f"Updated pitch_deg to {self.pitch_deg}")

            elif param.name == 'yaw_deg' and self.pipeline is not None:
                self.pipeline.set_yaw_deg(param.value)
                self.get_logger().info(f"Updated yaw_deg to {self.yaw_deg}")

            elif param.name == 'roll_deg' and self.pipeline is not None:
                self.pipeline.set_roll_deg(param.value)
                self.get_logger().info(f"Updated roll_deg to {self.roll_deg}")

            elif param.name == 'min_radius' and self.pipeline is not None:
                self.pipeline.set_min_radius(param.value)
                self.get_logger().info(f"Updated min_radius to {self.min_radius}")

            elif param.name == 'max_radius' and self.pipeline is not None:
                self.pipeline.set_max_radius(param.value)
                self.get_logger().info(f"Updated max_radius to {self.max_radius}")

            elif param.name == 'dist_coeffs' and self.pipeline is not None:
                self.pipeline.set_dist_coeffs(param.value)
                self.get_logger().info(f"Updated dist_coeffs to {self.dist_coeffs}")

        return result
    
    def get_statistics(self):
        """Return current performance statistics"""
        if not self.processing_times:
            return None
        
        return {
            'frame_count': self.frame_count,
            'avg_processing_ms': np.mean(self.processing_times),
            'std_processing_ms': np.std(self.processing_times),
            'fps': 1000.0 / np.mean(self.processing_times) if np.mean(self.processing_times) > 0 else 0,
            'error_counter': self.consecutive_error_counter
        }


def main(args=None):
    """Main entry point for the ROS2 node"""
    rclpy.init(args=args)
    node = RoadDetectorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutdown requested by user")
    except Exception as e:
        node.get_logger().error(f"Unexpected error: {e}")
    finally:
        # Print final statistics
        stats = node.get_statistics()
        if stats:
            node.get_logger().info(f"Final statistics: {stats}")
        
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()