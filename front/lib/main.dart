import 'package:flutter/material.dart';
import 'package:camera/camera.dart'; // Uncommented this so Camera works
import 'package:flutter_application_1/auth/signup/role_screen.dart';
import 'package:flutter_application_1/role_gate.dart';

// Imports
import 'theme/app_colors.dart';
import 'features/individual/navigation.dart'; 
import 'user_role.dart'; 
import 'auth/login_screen.dart';
import 'auth/signup/role_screen.dart';


// 1. Global Camera Variable
// We need this to pass the camera list to the CameraScreen later
List<CameraDescription> cameras = []; 

Future<void> main() async {
  // 2. Ensure bindings are initialized before calling native code
  WidgetsFlutterBinding.ensureInitialized();

  // 3. Initialize Camera
  try {
    cameras = await availableCameras();
  } on CameraException catch (e) {
    print('Error initializing camera: $e');
  }

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Profile Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: AppColors.background),
        useMaterial3: true,
      ),
      
      
      home: RoleGate()
    );
  }
}