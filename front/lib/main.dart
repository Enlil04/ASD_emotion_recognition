import 'package:flutter/material.dart';
// import 'package:camera/camera.dart'; // <--- COMMENTED OUT

// Imports
import 'theme/app_colors.dart';
import 'features/individual/navigation.dart'; 
import 'user_role.dart'; 

// 1. Global Camera Variable
// We leave this as an empty list so CameraScreen doesn't crash on compile
// List<CameraDescription> cameras = []; 
// ALTERNATIVE: If CameraScreen needs this type, keep the import or just make it dynamic for now:
List<dynamic> cameras = []; 

Future<void> main() async {
  // 2. Ensure bindings are initialized before calling native code
  WidgetsFlutterBinding.ensureInitialized();

  // --- COMMENTED OUT CAMERA LOGIC ---
  // try {
  //   cameras = await availableCameras();
  // } on CameraException catch (e) {
  //   print('Error initializing camera: $e');
  // }
  // ----------------------------------

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
      
      // -----------------------------------------------------------
      // CHANGE THIS LINE TO TEST DIFFERENT ROLES:
      // -----------------------------------------------------------
      
      // Option A: Test as Parent (Guardian)
      // Make sure your Enum matches this (UserRole.parent or UserRole.guardian)
      home: const MainScaffold(userRole: UserRole.guardian),

      // Option B: Test as Child (Individual)
      // home: const MainScaffold(userRole: UserRole.individual),
    );
  }
}
// import 'package:flutter/material.dart';

// // import 'package:camera/camera.dart'; 

// // Core
// import './theme/app_colors.dart';

// // Navigation
// import 'features/individual/navigation.dart';

// void main() {

  
//   runApp(const MyApp());
// }

// class MyApp extends StatelessWidget {
//   const MyApp({super.key});

//   @override
//   Widget build(BuildContext context) {
//     return MaterialApp(
//       debugShowCheckedModeBanner: false,
//       title: 'Profile Demo',
//       theme: ThemeData(
//         colorScheme: ColorScheme.fromSeed(
//           seedColor: AppColors.background,
//         ),
//         useMaterial3: true,
//       ),
//       home: const MainScaffold(),
//     );
//   }
// }
