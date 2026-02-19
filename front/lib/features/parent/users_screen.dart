import 'package:flutter/material.dart';
import '/../theme/app_colors.dart';
import '../../services/api_service.dart';
import '../individual/dashboard.dart';

class UsersScreen extends StatefulWidget {
  const UsersScreen({super.key});

  @override
  State<UsersScreen> createState() => _UsersScreenState();
}

class _UsersScreenState extends State<UsersScreen> {
  String? _role;
  String? _userId;
  Future<List<dynamic>>? _patientsFuture;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final role = (await ApiService.getRole() ?? "").toLowerCase();
    final userId = await ApiService.getUserId();

    if (!mounted) return;

    setState(() {
      _role = role;
      _userId = userId;
    });

    if (role == "therapist" || role == "parent") {
      if (userId == null || userId.isEmpty) return;
      setState(() {
        _patientsFuture = ApiService.fetchMyPatients();
      });
    }
  }

  Color _avatarColorFromName(String name) {
    // deterministic but simple
    final hash = name.codeUnits.fold<int>(0, (a, b) => a + b);
    final colors = <Color>[
      Colors.blueAccent,
      Colors.orangeAccent,
      Colors.purpleAccent,
      Colors.green,
      Colors.teal,
      Colors.redAccent,
      Colors.indigo,
    ];
    return colors[hash % colors.length];
  }

  Widget _buildPatientTile(BuildContext context, Map<String, dynamic> p) {
    final name = (p["name"] ?? "Unnamed").toString();
    final username = (p["username"] ?? "-").toString();
    final age = p["age"]?.toString() ?? "-";
    final photo = p["photo"]?.toString();

    final avatarColor = _avatarColorFromName(name);

    return Container(
      margin: const EdgeInsets.only(bottom: 15),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.blue.withOpacity(0.3)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
       onTap : () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => DashboardInsightsScreen(
              userId: p["user_id"],
              title: "${p["name"] ?? "Patient"} • Dashboard",
            ),
          ),
        );

          // // Next step later: open patient dashboard/stats
          // Navigator.push(
          //   context,
          //   MaterialPageRoute(
          //     builder: (_) => PatientDetailPlaceholder(
          //       patientId: (p["user_id"] ?? "").toString(),
          //       name: name,
          //       username: username,
          //       age: age,
          //       photo: photo,
          //     ),
          //   ),
          // );
        },
        leading: CircleAvatar(
          radius: 28,
          backgroundColor: avatarColor.withOpacity(0.2),
          backgroundImage: (photo != null && photo.isNotEmpty)
              ? NetworkImage(photo)
              : null,
          child: (photo == null || photo.isEmpty)
              ? Text(
                  name.isNotEmpty ? name[0].toUpperCase() : "?",
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: avatarColor,
                  ),
                )
              : null,
        ),
        title: Padding(
          padding: const EdgeInsets.only(bottom: 6.0),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text(
                  name,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 18,
                    color: AppColors.textDark,
                  ),
                ),
              ),
              Text(
                "Age: $age",
                style: TextStyle(fontSize: 12, color: Colors.grey[400]),
              ),
            ],
          ),
        ),
        subtitle: Row(
          children: [
            const Icon(Icons.person_outline, size: 16, color: Colors.grey),
            const SizedBox(width: 5),
            Expanded(
              child: Text(
                "Username: $username",
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: Colors.grey[600]),
              ),
            ),
          ],
        ),
        trailing: const Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isGuardian = _role == "therapist" || _role == "parent";

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text(
          'Connected Users',
          style: TextStyle(color: AppColors.textDark, fontWeight: FontWeight.bold),
        ),
        backgroundColor: AppColors.background,
        elevation: 0,
        centerTitle: true,
        automaticallyImplyLeading: false,
        actions: [
          if (isGuardian)
            IconButton(
              tooltip: "Refresh",
              onPressed: () {
                if (_userId == null || _userId!.isEmpty) return;
                setState(() {
                  _patientsFuture = ApiService.fetchMyPatients();
                });
              },
              icon: const Icon(Icons.refresh, color: AppColors.textDark),
            ),
        ],
      ),
      body: SafeArea(
        child: _role == null
            ? const Center(child: CircularProgressIndicator())
            : (!isGuardian)
                ? const Center(
                    child: Text(
                      "Only therapists or parents can view connected users.",
                      style: TextStyle(fontSize: 16, color: AppColors.textDark),
                      textAlign: TextAlign.center,
                    ),
                  )
                : FutureBuilder<List<dynamic>>(
                    future: _patientsFuture,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState == ConnectionState.waiting) {
                        return const Center(child: CircularProgressIndicator());
                      }

                      if (snapshot.hasError) {
                        return Center(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Text(
                              "Error loading patients:\n${snapshot.error}",
                              style: const TextStyle(color: AppColors.textDark),
                              textAlign: TextAlign.center,
                            ),
                          ),
                        );
                      }

                      final patients = snapshot.data ?? [];

                      if (patients.isEmpty) {
                        return const Center(
                          child: Text(
                            "No users connected yet.\nUse Profile → Connection to share your code.",
                            style: TextStyle(fontSize: 16, color: AppColors.textDark),
                            textAlign: TextAlign.center,
                          ),
                        );
                      }

                      return ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: patients.length,
                        itemBuilder: (context, index) {
                          final p = patients[index] as Map<String, dynamic>;
                          return _buildPatientTile(context, p);
                        },
                      );
                    },
                  ),
      ),
    );
  }
}

/// Placeholder screen (keeps your old navigation behavior).
/// Next step: replace this with the real patient dashboard view.
class PatientDetailPlaceholder extends StatelessWidget {
  final String patientId;
  final String name;
  final String username;
  final String age;
  final String? photo;

  const PatientDetailPlaceholder({
    super.key,
    required this.patientId,
    required this.name,
    required this.username,
    required this.age,
    required this.photo,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(
          "$name",
          style: const TextStyle(color: AppColors.textDark),
        ),
        backgroundColor: AppColors.background,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppColors.textDark),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Patient ID: $patientId", style: const TextStyle(color: AppColors.textDark)),
            const SizedBox(height: 10),
            Text("Username: $username", style: const TextStyle(color: AppColors.textDark)),
            const SizedBox(height: 10),
            Text("Age: $age", style: const TextStyle(color: AppColors.textDark)),
            const SizedBox(height: 24),
            const Text(
              "Next step: open this patient’s emotion dashboard here.",
              style: TextStyle(color: AppColors.textDark),
            ),
          ],
        ),
      ),
    );
  }
}


// import 'package:flutter/material.dart';
// import '/../theme/app_colors.dart'; 
// import '../../services/api_service.dart';
// // ---------------------------------------------------------
// // 1. DATA MODELS (To structure your data)
// // ---------------------------------------------------------
// class ConnectedUser {
//   final String name;
//   final String lastNotification;
//   final String lastActive;
//   final Color avatarColor;
//   final List<ActivityDetection> weeklyActivity;

//   ConnectedUser({
//     required this.name,
//     required this.lastNotification,
//     required this.lastActive,
//     required this.avatarColor,
//     required this.weeklyActivity,
//   });
// }

// class ActivityDetection {
//   final String label;
//   final String date;
//   final String time;
//   final Color color;

//   ActivityDetection({
//     required this.label,
//     required this.date,
//     required this.time,
//     required this.color,
//   });
// }

// // ---------------------------------------------------------
// // 2. USERS SCREEN (The List)
// // ---------------------------------------------------------
// class UsersScreen extends StatelessWidget {
//   UsersScreen({super.key});

//   // Mock Data
//   final List<ConnectedUser> users = [
//     ConnectedUser(
//       name: "Alex",
//       lastNotification: "High stress detected during homework",
//       lastActive: "2 mins ago",
//       avatarColor: Colors.blueAccent,
//       weeklyActivity: [
//         ActivityDetection(label: "High Stress", date: "Today", time: "4:30 PM", color: Colors.redAccent),
//         ActivityDetection(label: "Focused", date: "Yesterday", time: "2:00 PM", color: Colors.blue),
//         ActivityDetection(label: "Happy", date: "Mon", time: "10:00 AM", color: Colors.green),
//       ],
//     ),
//     ConnectedUser(
//       name: "Sarah",
//       lastNotification: "Completed daily check-in",
//       lastActive: "1 hour ago",
//       avatarColor: Colors.orangeAccent,
//       weeklyActivity: [
//         ActivityDetection(label: "Calm", date: "Today", time: "9:00 AM", color: Colors.purple),
//         ActivityDetection(label: "Happy", date: "Yesterday", time: "6:15 PM", color: Colors.green),
//       ],
//     ),
//   ];

//   @override
//   Widget build(BuildContext context) {
//     return Scaffold(
//       backgroundColor: AppColors.background,
//       appBar: AppBar(
//         title: const Text(
//           'Connected Users',
//           style: TextStyle(color: AppColors.textDark, fontWeight: FontWeight.bold),
//         ),
//         backgroundColor: AppColors.background,
//         elevation: 0,
//         centerTitle: true,
//         automaticallyImplyLeading: false,
//       ),
//       body: SafeArea(
//         child: ListView.builder(
//           padding: const EdgeInsets.all(16),
//           itemCount: users.length,
//           itemBuilder: (context, index) {
//             final user = users[index];
//             return _buildUserTile(context, user);
//           },
//         ),
//       ),
//     );
//   }

//   Widget _buildUserTile(BuildContext context, ConnectedUser user) {
//     return Container(
//       margin: const EdgeInsets.only(bottom: 15),
//       decoration: BoxDecoration(
//         color: Colors.white,
//         borderRadius: BorderRadius.circular(16),
//         border: Border.all(color: AppColors.blue.withOpacity(0.3)),
//         boxShadow: [
//           BoxShadow(
//             color: Colors.black.withOpacity(0.05),
//             blurRadius: 10,
//             offset: const Offset(0, 4),
//           ),
//         ],
//       ),
//       child: ListTile(
//         contentPadding: const EdgeInsets.all(16),
//         onTap: () {
//           // Navigate to details
//           Navigator.push(
//             context,
//             MaterialPageRoute(
//               builder: (context) => UserDetailScreen(user: user),
//             ),
//           );
//         },
//         // 1. ICON (Avatar)
//         leading: CircleAvatar(
//           radius: 28,
//           backgroundColor: user.avatarColor.withOpacity(0.2),
//           child: Text(
//             user.name[0], // First letter of name
//             style: TextStyle(
//               fontSize: 24,
//               fontWeight: FontWeight.bold,
//               color: user.avatarColor,
//             ),
//           ),
//         ),
//         // 2. NAME & LAST ACTIVE
//         title: Padding(
//           padding: const EdgeInsets.only(bottom: 6.0),
//           child: Row(
//             mainAxisAlignment: MainAxisAlignment.spaceBetween,
//             children: [
//               Text(
//                 user.name,
//                 style: const TextStyle(
//                   fontWeight: FontWeight.bold,
//                   fontSize: 18,
//                   color: AppColors.textDark,
//                 ),
//               ),
//               Text(
//                 user.lastActive,
//                 style: TextStyle(fontSize: 12, color: Colors.grey[400]),
//               ),
//             ],
//           ),
//         ),
//         // 3. LAST RECEIVED NOTIFICATION
//         subtitle: Row(
//           children: [
//             const Icon(Icons.notifications_none, size: 16, color: Colors.grey),
//             const SizedBox(width: 5),
//             Expanded(
//               child: Text(
//                 user.lastNotification,
//                 maxLines: 1,
//                 overflow: TextOverflow.ellipsis,
//                 style: TextStyle(color: Colors.grey[600]),
//               ),
//             ),
//           ],
//         ),
//         trailing: const Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey),
//       ),
//     );
//   }
// }

// // ---------------------------------------------------------
// // 3. USER DETAIL SCREEN (The Weekly Report)
// // ---------------------------------------------------------
// class UserDetailScreen extends StatelessWidget {
//   final ConnectedUser user;

//   const UserDetailScreen({super.key, required this.user});

//   @override
//   Widget build(BuildContext context) {
//     return Scaffold(
//       backgroundColor: AppColors.background,
//       appBar: AppBar(
//         title: Text(
//           "${user.name}'s Report",
//           style: const TextStyle(color: AppColors.textDark),
//         ),
//         backgroundColor: AppColors.background,
//         elevation: 0,
//         iconTheme: const IconThemeData(color: AppColors.textDark),
//       ),
//       body: SingleChildScrollView(
//         padding: const EdgeInsets.all(20),
//         child: Column(
//           crossAxisAlignment: CrossAxisAlignment.start,
//           children: [
//             // Header Profile
//             Center(
//               child: Column(
//                 children: [
//                   CircleAvatar(
//                     radius: 40,
//                     backgroundColor: user.avatarColor.withOpacity(0.2),
//                     child: Text(
//                       user.name[0],
//                       style: TextStyle(fontSize: 40, color: user.avatarColor, fontWeight: FontWeight.bold),
//                     ),
//                   ),
//                   const SizedBox(height: 10),
//                   Text(
//                     user.name,
//                     style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.textDark),
//                   ),
//                   Text(
//                     "Connected",
//                     style: TextStyle(color: Colors.green[600], fontWeight: FontWeight.w500),
//                   )
//                 ],
//               ),
//             ),
            
//             const SizedBox(height: 30),
            
//             // Section Title
//             const Text(
//               "Last Week's Activity",
//               style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textDark),
//             ),
            
//             const SizedBox(height: 15),

//             // Activity List
//             ...user.weeklyActivity.map((activity) => _buildActivityRow(activity)),
            
//             // Empty state check
//             if (user.weeklyActivity.isEmpty)
//               const Padding(
//                 padding: EdgeInsets.symmetric(vertical: 20),
//                 child: Center(child: Text("No activity recorded last week.")),
//               ),
//           ],
//         ),
//       ),
//     );
//   }

//   Widget _buildActivityRow(ActivityDetection activity) {
//     return Container(
//       margin: const EdgeInsets.only(bottom: 12),
//       padding: const EdgeInsets.all(16),
//       decoration: BoxDecoration(
//         color: Colors.white,
//         borderRadius: BorderRadius.circular(12),
//         border: Border.all(color: AppColors.blue.withOpacity(0.2)),
//       ),
//       child: Row(
//         children: [
//           Container(
//             padding: const EdgeInsets.all(10),
//             decoration: BoxDecoration(
//               color: activity.color.withOpacity(0.1),
//               shape: BoxShape.circle,
//             ),
//             child: Icon(Icons.show_chart, color: activity.color, size: 20),
//           ),
//           const SizedBox(width: 15),
//           Expanded(
//             child: Column(
//               crossAxisAlignment: CrossAxisAlignment.start,
//               children: [
//                 Text(
//                   activity.label,
//                   style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.textDark),
//                 ),
//                 Text(
//                   "Detected via Camera",
//                   style: TextStyle(fontSize: 12, color: Colors.grey[500]),
//                 ),
//               ],
//             ),
//           ),
//           Column(
//             crossAxisAlignment: CrossAxisAlignment.end,
//             children: [
//               Text(
//                 activity.date,
//                 style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.textDark),
//               ),
//               Text(
//                 activity.time,
//                 style: TextStyle(fontSize: 12, color: Colors.grey[500]),
//               ),
//             ],
//           )
//         ],
//       ),
//     );
//   }
// }