//import 'dart:async';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import '../../theme/app_colors.dart';
import '../../services/api_service.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> with AutomaticKeepAliveClientMixin {
  CameraController? _controller;
  bool _isCameraInitialized = false;
  
  // STATE VARIABLES
  bool _isRecording = false; 
  bool _isAnalyzing = false; 
  //int _timeLeft = 5;
  //Timer? _timer;

  // STATIC MEMORY
  static List<Map<String, dynamic>> _recentSessions = [];

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    if (_controller != null && _controller!.value.isInitialized) {
      if (mounted) setState(() => _isCameraInitialized = true);
      return;
    }

    if (_isCameraInitialized) return; 

    try {
      final cameras = await availableCameras();
      
      if (cameras.isEmpty) {
        debugPrint("❌ No cameras found on device!");
        return;
      }

      CameraDescription camera = cameras.first;
      for (var cam in cameras) {
        if (cam.lensDirection == CameraLensDirection.front) {
          camera = cam;
          break;
        }
      }

      _controller = CameraController(
        camera, 
        ResolutionPreset.medium, 
        enableAudio: false, 
      );

      await _controller!.initialize();
      
      if (mounted) {
        setState(() => _isCameraInitialized = true);
      }
      
    } catch (e) {
      debugPrint("❌ Camera Initialization Error: $e");
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    //_timer?.cancel();
    super.dispose();
  }

  // void _startSession() async {
  //   if (!_isCameraInitialized || _isRecording || _isAnalyzing) return;

  //   try {
  //     await _controller!.startVideoRecording();
      
  //     setState(() {
  //       _isRecording = true;
  //       _timeLeft = 5; 
  //     });

  //     _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
  //       if (mounted) {
  //         if (_timeLeft > 0) {
  //           setState(() => _timeLeft--);
  //         } else {
  //           _stopSession(); 
  //         }
  //       }
  //     });

  //   } catch (e) {
  //     debugPrint("Error starting: $e");
  //   }
  // }

  // void _stopSession() async {
  //   _timer?.cancel();
  //   if (!_isRecording) return;

  //   try {
  //     final XFile videoFile = await _controller!.stopVideoRecording();
      
  //     setState(() {
  //       _isRecording = false;
  //       _isAnalyzing = true; 
  //     });

  //     // API Call
  //     Map<String, dynamic> result = await ApiService.analyzeSession(videoFile.path);
      
  //     String emotion = result['dominant_emotion'] ?? "Unknown";
  //     dynamic rawConf = result['confidence'] ?? 0;
  //     int confidence = (rawConf is double) ? rawConf.toInt() : (rawConf as int);
      
  //     if (mounted) {
  //       setState(() {
  //         _isAnalyzing = false;
  //         _timeLeft = 5; 
          
  //         _recentSessions.insert(0, {
  //           "label": emotion,
  //           "confidence": confidence,
  //           "time": _getCurrentTime(),
  //           "color": _getColorForEmotion(emotion),
  //         });
  //       });
  //     }

  //   } catch (e) {
  //     debugPrint("Error stopping: $e");
  //     if (mounted) {
  //       setState(() {
  //         _isRecording = false;
  //         _isAnalyzing = false;
  //       });
  //     }
  //   }
  // }
  Future<void> _capturePhoto() async {
  if (!_isCameraInitialized || _isAnalyzing) return;

  try {
    setState(() {
      _isAnalyzing = true;
    });

    final XFile imageFile = await _controller!.takePicture();

    // API Call (image)
    final Map<String, dynamic> result = await ApiService.analyzeImage(imageFile.path);

    final String emotion = (result['dominant_emotion'] ?? "Unknown").toString();
    final dynamic rawConf = result['confidence'] ?? 0;

    // your backend returns confidence as %
    final int confidence = (rawConf is num) ? rawConf.round() : 0;

    if (!mounted) return;

    setState(() {
      _isAnalyzing = false;

      _recentSessions.insert(0, {
        "label": emotion,
        "confidence": confidence,
        "time": _getCurrentTime(),
        "color": _getColorForEmotion(emotion),
      });
    });
  } catch (e) {
    debugPrint("Error capturing image: $e");
    if (!mounted) return;
    setState(() {
      _isAnalyzing = false;
    });
  }
}


  String _getCurrentTime() {
    final now = DateTime.now();
    return "${now.hour}:${now.minute.toString().padLeft(2, '0')}";
  }

  Color _getColorForEmotion(String emotion) {
    switch (emotion.toLowerCase()) {
      case 'happy': return Colors.green;
      case 'sad': return Colors.blueGrey;
      case 'angry': return Colors.red;
      case 'surprised': return Colors.orange;
      case 'neutral': return Colors.blue;
      case 'disgust': return Colors.brown;
      case 'fear': return Colors.indigo;
      default: return Colors.purple;
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context); 

    // Define the height here for consistency
    final double cameraHeight = 500; 

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Mood Session', style: TextStyle(color: AppColors.titletext, fontWeight: FontWeight.w500)),
        backgroundColor: AppColors.background,
        elevation: 0,
        automaticallyImplyLeading: false,
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                child: Padding(
                  // Reduced padding to 10.0 to make the camera window wider
                  padding: const EdgeInsets.symmetric(horizontal: 25.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 5),

                      // --- LIVE CAMERA FEED ---
                      Container(
                        height: cameraHeight, 
                        width: double.infinity, 
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            Container(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(20),
                                border: Border.all(
                                  color: _isRecording ? AppColors.textDark : AppColors.lighterblue, 
                                  width: 3
                                ),
                              ),
                              // ClipRRect creates the rounded corners
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(16),
                                child: SizedBox(
                                  width: double.infinity,
                                  height: cameraHeight,
                                  child: _isCameraInitialized
                                      ? FittedBox(
                                          fit: BoxFit.cover, // Ensures video fills the tall box
                                          child: SizedBox(
                                            // We swap width/height because phone cameras are often rotated 90 degrees
                                            width: _controller!.value.previewSize!.height,
                                            height: _controller!.value.previewSize!.width,
                                            child: CameraPreview(_controller!),
                                          ),
                                        )
                                      : const Center(child: CircularProgressIndicator()),
                                ),
                              ),
                            ),
                            
                            // Recording Overlay
                            if (_isRecording)
                              Positioned(
                                bottom: 20,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                  decoration: BoxDecoration(
                                    color: AppColors.lighterblue.withOpacity(0.8),
                                    borderRadius: BorderRadius.circular(20),
                                  ),
            
                                ),
                              ),

                            // Analyzing Overlay
                            if (_isAnalyzing)
                              Container(
                                width: double.infinity,
                                height: cameraHeight,
                                decoration: BoxDecoration(
                                  color: AppColors.textDark.withOpacity(0.2),
                                  borderRadius: BorderRadius.circular(20),
                                ),
                                child: const Center(
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      CircularProgressIndicator(color: Colors.white),
                                      SizedBox(height: 10),
                                      Text("Analyzing Mood...", style: TextStyle(color: Colors.white)),
                                    ],
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 25),
                      const Text("Session History", style: TextStyle(color: AppColors.textDark, fontSize: 16, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 15),

                      if (_recentSessions.isEmpty)
                        const Padding(padding: EdgeInsets.all(20.0),
                          child: Text("Start a session to track your mood.", style: TextStyle(color: AppColors.textDark, fontSize: 14, fontWeight: FontWeight.normal)),
                        )
                      else
                        Column(
                          children: _recentSessions.map((d) => _buildSessionRow(d)).toList(),
                        ),
                    ],
                  ),
                ),
              ),
            ),

            // --- START BUTTON ---
            Padding(
              padding: const EdgeInsets.only(top: 9, bottom: 30),
              child: GestureDetector(
                onTap: _isAnalyzing ? null : _capturePhoto, 
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  height: 80,
                  width: 80,
                  decoration: BoxDecoration(
                    color: _isRecording ? Colors.grey[300] : AppColors.lighterblue, 
                    shape: BoxShape.circle,
                    boxShadow: [
                      if (!_isRecording)
                        BoxShadow(color: AppColors.lighterblue.withOpacity(0.4), blurRadius: 15, offset: const Offset(0, 5))
                    ],
                  ),
                  child: Center(
                    child: Icon(
                        _isAnalyzing ? Icons.hourglass_bottom : Icons.camera_alt,
                        color: Colors.white,
                        size: 35,
                      ),
                  ),
                ),
              ),
            ),
           if (!_isAnalyzing)
              const Padding(
                padding: EdgeInsets.only(bottom: 20),
                child: Text("Tap to take a photo", style: TextStyle(color: AppColors.textDark)),
              )

          ],
        ),
      ),
    );
  }

  Widget _buildSessionRow(Map<String, dynamic> data) { 
    return Container( 
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16), 
        boxShadow: [BoxShadow(color: AppColors.textDark.withOpacity(0.12), blurRadius: 5, offset: const Offset(0, 2))], 
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: (data['color'] as Color).withOpacity(0.1), shape: BoxShape.circle),
            child: Icon(Icons.psychology, color: data['color'], size: 24),
          ),
          const SizedBox(width: 15),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "${data['label']} (${data['confidence']}%)", 
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.textDark)
                ),
                Text("Session at ${data['time']}", style: TextStyle(fontSize: 12, color: AppColors.textDark.withOpacity(0.6))),
              ],
            ),
          ),
        ],
      ),
    );
  }
}