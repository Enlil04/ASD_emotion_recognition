import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // ⚠️ IMPORTANT: Replace with your PC's IPv4 Address
  // If using Android Emulator, use '10.0.2.2' instead of local IP
  static const String baseUrl = "http://10.128.189.50:8000"; //uhave to chnage this

  static Future<String> sendMessage(String message) async {
    try {
      final url = Uri.parse('$baseUrl/chat');
      
      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "user_id": "user_001", // Hardcoded for now
          "message": message
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['response']; // The text from Llama
      } else {
        return "Error: Server returned ${response.statusCode}";
      }
    } catch (e) {
      return "Error connecting to Agent: $e";
    }
  }
}