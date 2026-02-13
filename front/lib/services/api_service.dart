import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart'; 
import 'package:flutter_secure_storage/flutter_secure_storage.dart';


class ApiService {
  
  static const String baseUrl = 'http://10.242.197.50:8000';
  static const _storage = FlutterSecureStorage();

//------------------------ register here ---------------------------------
  static Future<Map<String, dynamic>> register({
  required String email,
  required String password,
  required String role, // "therapist" | "parent" | "user"
  String? username,
  String? name,
  String? dob,
  Map<String, dynamic>? extra,
}) async {
  final url = Uri.parse('$baseUrl/auth/register');

  final res = await http.post(
    url,
    headers: {"Content-Type": "application/json"},
    body: jsonEncode({
      "email": email.trim(),
      "password": password,
      "role": role.toLowerCase().trim(),
      "username": username?.trim(),
      "name": name?.trim(),
      "dob": dob,               // "YYYY-MM-DD"
      "extra": extra ?? {},     // role-specific fields
    }),
  ).timeout(const Duration(seconds: 30));

  if (res.statusCode == 200) {
    return jsonDecode(res.body) as Map<String, dynamic>;
  }
  throw Exception("Register failed: ${res.statusCode} ${res.body}");
}
//------------------------------------------------------------------------------


//--------------------------------login helpers and methods here --------------------------------------

static Future<void> saveSession({
  required String token,
  required String role,
  required String userId,
}) async {
  await _storage.write(key: "access_token", value: token);
  await _storage.write(key: "role", value: role);
  await _storage.write(key: "user_id", value: userId);
}

static Future<String?> getToken() => _storage.read(key: "access_token");
static Future<String?> getRole() => _storage.read(key: "role");
static Future<String?> getUserId() => _storage.read(key: "user_id");

static Future<void> logout() async {
  await _storage.delete(key: "access_token");
  await _storage.delete(key: "role");
  await _storage.delete(key: "user_id");
}

static Future<Map<String, String>> authHeaders() async {
  final token = await getToken();
  return {
    "Content-Type": "application/json",
    if (token != null) "Authorization": "Bearer $token",
  };
}

static Future<Map<String, dynamic>> login({
  required String email,
  required String password,
}) async {
  final url = Uri.parse('$baseUrl/auth/login');

  final res = await http.post(
    url,
    headers: {"Content-Type": "application/json"},
    body: jsonEncode({
      "email": email.trim(),
      "password": password,
    }),
  ).timeout(const Duration(seconds: 30));

  if (res.statusCode != 200) {
    throw Exception("Login failed: ${res.statusCode} ${res.body}");
  }

  final data = jsonDecode(res.body) as Map<String, dynamic>;

  await saveSession(
    token: data["access_token"],
    role: data["role"],
    userId: data["user_id"],
  );

  return data;
}

//-------------------------------------------------------------------------------------------------------


// -------------------- PROFILE (new) --------------------

static Future<Map<String, dynamic>> fetchProfileStats(String userId) async {
  final token = await getToken();
  final url = Uri.parse('$baseUrl/api/profile/stats?user_id=$userId');

  final res = await http.get(
    url,
    headers: {
      "Content-Type": "application/json",
      if (token != null) "Authorization": "Bearer $token",
    },
  ).timeout(const Duration(seconds: 15));

  if (res.statusCode == 200) {
    return jsonDecode(res.body) as Map<String, dynamic>;
  }
  throw Exception("Failed to load profile stats: ${res.statusCode} ${res.body}");
}

static Future<List<dynamic>> fetchProfileActivity(String userId,
    {int limit = 10, int offset = 0}) async {
  final token = await getToken();
  final url = Uri.parse(
    '$baseUrl/api/profile/activity?user_id=$userId&limit=$limit&offset=$offset',
  );

  final res = await http.get(
    url,
    headers: {
      "Content-Type": "application/json",
      if (token != null) "Authorization": "Bearer $token",
    },
  ).timeout(const Duration(seconds: 15));

  if (res.statusCode == 200) {
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return (data["items"] as List<dynamic>? ?? []);
  }
  throw Exception("Failed to load activity: ${res.statusCode} ${res.body}");
}
//-------------------------------------------------------------------------

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
      ).timeout(const Duration(seconds: 180)); 

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
      
      request.files.add(
        await http.MultipartFile.fromPath(
          'file', 
          videoPath,
          contentType: MediaType('video', 'mp4'), 
        )
      );

      var streamedResponse = await request.send().timeout(const Duration(seconds: 30));
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

  // --- NEW METHODS FOR DASHBOARD ---

  static Future<Map<String, dynamic>> fetchWeeklyEmotions(String userId) async {
    final url = Uri.parse("$baseUrl/api/emotions/weekly?user_id=$userId");
    final response = await http.get(url);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("Weekly endpoint failed: ${response.statusCode}");
    }
  }

  static Future<Map<String, dynamic>> fetchDailyRecommendation(String userId) async {
    final url = Uri.parse("$baseUrl/api/recommendation/today?user_id=$userId");
    final response = await http.get(url);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("Recommendation endpoint failed: ${response.statusCode}");
    }
  }

  static Future<Map<String, dynamic>> fetchLatestEmotion(String userId) async {
  final url = Uri.parse("$baseUrl/api/emotions/latest?user_id=$userId");
  final response = await http.get(url);

  if (response.statusCode == 200) {
    return jsonDecode(response.body) as Map<String, dynamic>;
  } else {
    throw Exception("Latest emotion endpoint failed: ${response.statusCode}");
  }
}


  // ==============================
  // COMMUNITY ENDPOINTS
  // ==============================

  // (1) GET /api/community/posts  - Feed (paged)
  static Future<Map<String, dynamic>> fetchCommunityPosts({
    String? userId,
    int limit = 20,
    int offset = 0,
  }) async {
    final qs = <String, String>{
      "limit": "$limit",
      "offset": "$offset",
    };
    if (userId != null && userId.isNotEmpty) {
      qs["user_id"] = userId; // enables liked_by_me on backend
    }

    final url = Uri.parse("$baseUrl/api/community/posts").replace(queryParameters: qs);
    final response = await http.get(url);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("Community feed failed: ${response.statusCode} ${response.body}");
    }
  }

  // (2) POST /api/community/posts  - Create a post
  static Future<Map<String, dynamic>> createCommunityPost({
    required String userId,
    required String content,
  }) async {
    final url = Uri.parse("$baseUrl/api/community/posts");
    final response = await http.post(
      url,
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "user_id": userId,
        "content": content,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("Create post failed: ${response.statusCode} ${response.body}");
    }
  }

  // (3) GET /api/community/posts/{post_id}  - Post detail
  static Future<Map<String, dynamic>> fetchCommunityPostDetail({
    required int postId,
    String? userId,
  }) async {
    final url = (userId != null && userId.isNotEmpty)
        ? Uri.parse("$baseUrl/api/community/posts/$postId?user_id=$userId")
        : Uri.parse("$baseUrl/api/community/posts/$postId");

    final response = await http.get(url);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("Post detail failed: ${response.statusCode} ${response.body}");
    }
  }

  // (4) GET /api/community/posts/{post_id}/comments  - List comments
  static Future<Map<String, dynamic>> fetchPostComments({
    required int postId,
    int limit = 30,
    int offset = 0,
  }) async {
    final url = Uri.parse("$baseUrl/api/community/posts/$postId/comments")
        .replace(queryParameters: {
      "limit": "$limit",
      "offset": "$offset",
    });

    final response = await http.get(url);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("Fetch comments failed: ${response.statusCode} ${response.body}");
    }
  }

  // (5) POST /api/community/posts/{post_id}/comments  - Add comment
  static Future<Map<String, dynamic>> addPostComment({
    required int postId,
    required String userId,
    required String content,
  }) async {
    final url = Uri.parse("$baseUrl/api/community/posts/$postId/comments");
    final response = await http.post(
      url,
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "user_id": userId,
        "content": content,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("Add comment failed: ${response.statusCode} ${response.body}");
    }
  }

  // (6) POST /api/community/posts/{post_id}/like  - Like post
  static Future<Map<String, dynamic>> likePost({
    required int postId,
    required String userId,
  }) async {
    final url = Uri.parse("$baseUrl/api/community/posts/$postId/like");
    final response = await http.post(
      url,
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"user_id": userId}),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("Like failed: ${response.statusCode} ${response.body}");
    }
  }

  // (7) POST /api/community/posts/{post_id}/unlike  - Unlike post
  static Future<Map<String, dynamic>> unlikePost({
    required int postId,
    required String userId,
  }) async {
    final url = Uri.parse("$baseUrl/api/community/posts/$postId/unlike");
    final response = await http.post(
      url,
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"user_id": userId}),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("Unlike failed: ${response.statusCode} ${response.body}");
    }
  }

  // (8) GET /api/users/{user_id}  - Public user profile
  static Future<Map<String, dynamic>> fetchUserProfile(String userId) async {
    final url = Uri.parse("$baseUrl/api/users/$userId");
    final response = await http.get(url);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("User profile failed: ${response.statusCode} ${response.body}");
    }
  }

  // (9) POST /api/community/posts/{post_id}/report  - Report a post
  static Future<Map<String, dynamic>> reportPost({
    required int postId,
    required String reporterUserId,
    required String reason,
  }) async {
    final url = Uri.parse("$baseUrl/api/community/posts/$postId/report");
    final response = await http.post(
      url,
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "reporter_user_id": reporterUserId,
        "reason": reason,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("Report failed: ${response.statusCode} ${response.body}");
    }
  }

  // (10) DELETE /api/community/posts/{post_id}  - Delete post (soft delete)
  // NOTE: backend expects requester_user_id as query param (not JSON body)
  static Future<Map<String, dynamic>> deletePost({
    required int postId,
    required String requesterUserId,
  }) async {
    final url = Uri.parse("$baseUrl/api/community/posts/$postId")
        .replace(queryParameters: {"requester_user_id": requesterUserId});

    final response = await http.delete(url);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception("Delete post failed: ${response.statusCode} ${response.body}");
    }
  }

  // ==============================
// THERAPIST/PARENT <-> USER LINKING
// ==============================

static Future<String> fetchMyTherapistCode(String userId) async {
  final url = Uri.parse("$baseUrl/api/therapist/my_code?user_id=$userId");
  final response = await http.get(url);

  if (response.statusCode == 200) {
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return (data["code"] ?? "").toString();
  } else {
    throw Exception("Fetch code failed: ${response.statusCode} ${response.body}");
  }
}

static Future<String> regenerateTherapistCode(String userId) async {
  final url = Uri.parse("$baseUrl/api/therapist/regenerate_code");
  final response = await http.post(
    url,
    headers: {"Content-Type": "application/json"},
    body: jsonEncode({"user_id": userId}),
  );

  if (response.statusCode == 200) {
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return (data["code"] ?? "").toString();
  } else {
    throw Exception("Regenerate code failed: ${response.statusCode} ${response.body}");
  }
}

static Future<void> connectWithCode({
  required String patientId,
  required String code,
}) async {
  final url = Uri.parse("$baseUrl/api/therapist/connect");
  final response = await http.post(
    url,
    headers: {"Content-Type": "application/json"},
    body: jsonEncode({
      "patient_id": patientId,
      "code": code,
    }),
  );

  if (response.statusCode == 200) {
    return;
  } else {
    throw Exception("Connect failed: ${response.statusCode} ${response.body}");
  }
}

// Optional for later (therapist screen)
static Future<List<dynamic>> fetchMyPatients(String therapistId) async {
  final url = Uri.parse("$baseUrl/api/therapist/$therapistId/patients");
  final response = await http.get(url);

  if (response.statusCode == 200) {
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return (data["items"] as List<dynamic>? ?? []);
  } else {
    throw Exception("Fetch patients failed: ${response.statusCode} ${response.body}");
  }
}


}



