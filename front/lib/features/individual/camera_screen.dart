import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';

class CameraScreen extends StatelessWidget {
  const CameraScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text(
          'Camera',
          style: TextStyle(
            color: AppColors.titletext,
            fontWeight: FontWeight.w500,
            fontSize: 20,
          ),
        ),
        backgroundColor: AppColors.background,
        elevation: 0,
        automaticallyImplyLeading: false,
      ),
      body: SafeArea(
        child: Column(
          children: [
            // --- TOP SCROLLABLE SECTION ---
            Expanded(
              child: SingleChildScrollView(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 20),

                      // 1. CAMERA SQUARE
                      AspectRatio(
                        aspectRatio: 1.0,
                        child: Container(
                          decoration: BoxDecoration(
                            color: AppColors.blue,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: AppColors.lighterblue, width: 2),
                          ),
                          child: const Center(
                            child: Icon(Icons.camera_alt, size: 50, color: AppColors.lighterblue),
                          ),
                        ),
                      ),

                      const SizedBox(height: 25),

                      // 2. TITLE
                      const Text(
                        "Recent Detections",
                        style: TextStyle(
                          color: AppColors.lighterblue,
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                      ),

                      const SizedBox(height: 15),

                      // 3. VERTICAL LIST OF DETECTIONS
                      // We use a Column here so it scrolls with the rest of the page
                      Column(
                        children: [
                          _buildDetectionRow(
                            label: "Happy",
                            date: "Today, 10:42 AM",
                            color: Colors.green,
                          ),
                          _buildDetectionRow(
                            label: "Neutral",
                            date: "Today, 9:15 AM",
                            color: Colors.blue,
                          ),
                          _buildDetectionRow(
                            label: "Surprised",
                            date: "Yesterday, 8:30 PM",
                            color: Colors.orange,
                          ),
                          _buildDetectionRow(
                            label: "Calm",
                            date: "Yesterday, 6:00 PM",
                            color: Colors.purple,
                          ),
                        ],
                      ),
                      
                      const SizedBox(height: 20),
                    ],
                  ),
                ),
              ),
            ),

            // --- BOTTOM FIXED BUTTONS ---
            Padding(
              padding: const EdgeInsets.only(top: 10, bottom: 30),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    icon: const Icon(Icons.photo_library, size: 30, color: AppColors.lighterblue),
                    onPressed: () {},
                  ),
                  const SizedBox(width: 40),
                  GestureDetector(
                    onTap: () => print("Snap!"),
                    child: Container(
                      height: 80,
                      width: 80,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: AppColors.textDark.withOpacity(0.6),
                          width: 4,
                        ),
                        color: Colors.transparent,
                      ),
                      padding: const EdgeInsets.all(5),
                      child: Container(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppColors.textDark.withOpacity(0.6),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 40),
                  IconButton(
                    icon: const Icon(Icons.flip_camera_ios, size: 30, color: AppColors.lighterblue),
                    onPressed: () {},
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // --- NEW ROW WIDGET ---
  Widget _buildDetectionRow({
    required String label,
    required String date,
    required Color color,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12), // Spacing between rows
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.blue.withOpacity(0.3)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          // Icon Box
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.emoji_emotions, color: color, size: 24),
          ),
          
          const SizedBox(width: 15),
          
          // Text Details
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textDark,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  date,
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.textDark.withOpacity(0.6),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}