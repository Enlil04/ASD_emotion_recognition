import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart'; // Add this for MediaType

class ApiService {
  // 10.0.2.2 is for Android Emulator. Use your PC IP (e.g., 192.168.1.x) for physical phones.
  static const String baseUrl = 'http://10.0.2.2:8000';

  static Future<String> sendMessage(String message) async {
    try {
      final url = Uri.parse('$baseUrl/chat');
      
      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "user_id": "user_001", 
          "message": message
        }),
      ).timeout(const Duration(seconds: 15)); // Added timeout

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['response']; 
      } else {
        return "Error: Server returned ${response.statusCode}";
      }
    } catch (e) {
      return "Nimi is offline. Check your server connection.";
    }
  }

  static Future<Map<String, dynamic>> analyzeSession(String videoPath) async {
    try {
      var request = http.MultipartRequest(
        'POST', 
        Uri.parse('$baseUrl/api/analyze_session')
      );
      
      // Explicitly set the media type to video/mp4
      request.files.add(
        await http.MultipartFile.fromPath(
          'file', 
          videoPath,
          contentType: MediaType('video', 'mp4'), 
        )
      );

      var streamedResponse = await request.send().timeout(const Duration(seconds: 30)); // Longer timeout for video
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        return {"dominant_emotion": "Error", "confidence": 0.0};
      }
    } catch (e) {
      print("Error sending video: $e");
      return {"dominant_emotion": "Error", "confidence": 0.0};
    }
  }
}