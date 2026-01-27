import 'dart:async';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import '../../theme/app_colors.dart';
import '../../services/api_service.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraController? _controller;
  bool _isCameraInitialized = false;
  
  // STATE VARIABLES
  bool _isRecording = false; 
  bool _isAnalyzing = false; 
  int _timeLeft = 10;         // Set to 10 seconds
  Timer? _timer;

  List<Map<String, dynamic>> _recentSessions = [];

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    try {
      final cameras = await availableCameras();
      
      if (cameras.isEmpty) {
        print("❌ No cameras found on device!");
        return;
      }

      // SAFELY FIND A CAMERA:
      // Try to find the front camera, but if it doesn't exist, just use the first one (Back).
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
      if (mounted) setState(() => _isCameraInitialized = true);
      
    } catch (e) {
      print("❌ Camera Initialization Error: $e");
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    _timer?.cancel();
    super.dispose();
  }

  // --- 1. START THE 10-SECOND SESSION ---
  void _startSession() async {
    if (!_isCameraInitialized || _isRecording || _isAnalyzing) return;

    try {
      await _controller!.startVideoRecording();
      
      setState(() {
        _isRecording = true;
        _timeLeft = 10; // Ensure starts at 10
      });

      _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
        if (_timeLeft > 0) {
          setState(() => _timeLeft--);
        } else {
          _stopSession(); 
        }
      });

    } catch (e) {
      print("Error starting: $e");
    }
  }

  // --- 2. STOP & SEND TO PYTHON ---
  void _stopSession() async {
    _timer?.cancel();
    if (!_isRecording) return;

    try {
      final XFile videoFile = await _controller!.stopVideoRecording();
      
      setState(() {
        _isRecording = false;
        _isAnalyzing = true; 
      });

      // API Call
      Map<String, dynamic> result = await ApiService.analyzeSession(videoFile.path);
      
      String emotion = result['dominant_emotion'] ?? "Unknown";
      
      setState(() {
        _isAnalyzing = false;
        _timeLeft = 10; // Reset for next time
        
        _recentSessions.insert(0, {
          "label": emotion,
          "confidence": result['confidence'] ?? 0,
          "time": _getCurrentTime(),
          "color": _getColorForEmotion(emotion),
        });
      });

    } catch (e) {
      print("Error stopping: $e");
      setState(() {
        _isRecording = false;
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
      default: return Colors.purple;
    }
  }

  @override
  Widget build(BuildContext context) {
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
                  padding: const EdgeInsets.symmetric(horizontal: 20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 20),

                      // --- LIVE CAMERA FEED ---
                      AspectRatio(
                        aspectRatio: 1.0,
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            Container(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(20),
                                border: Border.all(
                                  color: _isRecording ? Colors.redAccent : AppColors.lighterblue, 
                                  width: 4
                                ),
                              ),
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(16),
                                child: _isCameraInitialized
                                    ? CameraPreview(_controller!)
                                    : const Center(child: CircularProgressIndicator()),
                              ),
                            ),
                            
                            if (_isRecording)
                              Positioned(
                                bottom: 20,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                  decoration: BoxDecoration(
                                    color: Colors.redAccent.withOpacity(0.8),
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: Text(
                                    "Recording: $_timeLeft s",
                                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ),

                            if (_isAnalyzing)
                              Container(
                                decoration: BoxDecoration(
                                  color: Colors.black.withOpacity(0.7),
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
                      const Text("Session History", style: TextStyle(color: AppColors.lighterblue, fontSize: 16, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 15),

                      if (_recentSessions.isEmpty)
                        const Padding(padding: EdgeInsets.all(20), child: Text("Start a session to track your mood."))
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
              padding: const EdgeInsets.only(top: 10, bottom: 30),
              child: GestureDetector(
                onTap: _isRecording ? null : _startSession, 
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  height: 80,
                  width: 80,
                  decoration: BoxDecoration(
                    color: _isRecording ? Colors.grey[300] : Colors.redAccent, 
                    shape: BoxShape.circle,
                    boxShadow: [
                      if (!_isRecording)
                        BoxShadow(color: Colors.redAccent.withOpacity(0.4), blurRadius: 15, offset: const Offset(0, 5))
                    ],
                  ),
                  child: Center(
                    child: Icon(
                      _isRecording ? Icons.hourglass_bottom : Icons.videocam,
                      color: Colors.white,
                      size: 35,
                    ),
                  ),
                ),
              ),
            ),
            if (!_isRecording && !_isAnalyzing)
              const Padding(
                padding: EdgeInsets.only(bottom: 20),
                child: Text("Tap to start 10s Session", style: TextStyle(color: AppColors.textDark)), // Updated text
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
        boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 5, offset: const Offset(0, 2))],
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
                  "${data['label']} (${data['confidence'].toInt()}%)", 
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