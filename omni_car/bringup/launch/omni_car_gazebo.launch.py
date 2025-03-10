from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.actions import TimerAction

def generate_launch_description():

    # Declare arguments
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            "rviz",
            default_value="false",
            description="Start RViz2 automatically with this launch file.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "rqt",
            default_value="false",
            description="Start rqt automatically with this launch file.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "joy",
            default_value="false",
            description="Start joy node automatically with this launch file.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "load_map",
            default_value="false",
            description="Start nav2_map_server node automatically with this launch file.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "navigation",
            default_value="false",
            description="Start navigation node automatically with this launch file.",
        )
    )

    # Initialize Arguments
    arg_rviz = LaunchConfiguration("rviz")
    arg_rqt = LaunchConfiguration("rqt")
    arg_joy = LaunchConfiguration("joy")
    arg_load_map = LaunchConfiguration("load_map")
    arg_navigation = LaunchConfiguration("navigation")

    # Get URDF via xacro
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]), " ",
            PathJoinSubstitution([FindPackageShare("omni_car"), "urdf", "omni_car.xacro"]), " ",
        ]
    )
    robot_description = {"robot_description": robot_description_content}

    world_sdf_file = PathJoinSubstitution([FindPackageShare("omni_car"), "gazebo", "world.sdf"])
    ekf_config_file = PathJoinSubstitution([FindPackageShare("omni_car"), "config", "ekf.yaml"])
    rviz_config_file = PathJoinSubstitution([FindPackageShare("omni_car"), "rviz", "rviz.rviz"])

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([FindPackageShare("ros_gz_sim"), "/launch/gz_sim.launch.py"]),
        launch_arguments={"gz_args": " -r -v 3 empty.sdf"}.items(),  # -v verbose level, -r run immediately 
    )

    gz_spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-topic", "/robot_description",
            "-name", "omni_car",
            "-allow_renaming", "true",
            "-z", "0.06"
        ],
    )
    gz_spawn_world = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-file", world_sdf_file,
            "-name", "world",
            "-allow_renaming", "true",
        ],
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description],
    )

    joint_state_publisher = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        parameters=[{'use_sim_time' : True}]
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    robot_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["omni_drive_controller", "--controller-manager", "/controller_manager"],
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
                   '/imu@sensor_msgs/msg/Imu@gz.msgs.IMU',
                   '/camera@sensor_msgs/msg/Image@gz.msgs.Image',
                   '/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo',
                   '/depth_camera@sensor_msgs/msg/Image@gz.msgs.Image'
                   ],
        output='screen'
    )

    joy = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([FindPackageShare("omni_car"), "/launch/teleop_twist_joy.launch.py"]),
        condition=IfCondition(arg_joy),
    )

    load_map = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([FindPackageShare("omni_car"), "/launch/map_server.launch.py"]),
        condition=IfCondition(arg_load_map),
    )

    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([FindPackageShare("omni_car"), "/launch/navigation.launch.py"]),
        condition=IfCondition(arg_navigation),
    )
    navigation_with_delay = TimerAction(
        period=15.0,
        actions=[navigation]
    )

    ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config_file],
    )
    ekf_with_delay = TimerAction(
        period=10.0,
        actions=[ekf]
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
        condition=IfCondition(arg_rviz),
    )
    rviz_with_delay = TimerAction(
        period=5.0,
        actions=[rviz]
    )
    rqt = Node(
        package='rqt_image_view',
        executable='rqt_image_view',
        arguments=['/camera'],
        condition=IfCondition(arg_rqt),
    )

    nodes = [
        gazebo,
        gz_spawn_entity,
        gz_spawn_world,
        joint_state_publisher,
        robot_state_publisher,
        joint_state_broadcaster_spawner,
        robot_controller_spawner,
        bridge,
        joy,
        load_map,
        navigation_with_delay,
        ekf_with_delay,
        rviz_with_delay,
        rqt
    ]

    return LaunchDescription(declared_arguments + nodes)
