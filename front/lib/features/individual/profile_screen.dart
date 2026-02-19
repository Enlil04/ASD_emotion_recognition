import 'package:flutter/material.dart';
import 'package:flutter_application_1/services/api_service.dart';
import '../../theme/app_colors.dart';
import 'dashboard.dart';
import '../../role_gate.dart';
import 'package:flutter/services.dart';


class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final GlobalKey<ScaffoldState> _profileScaffoldKey = GlobalKey<ScaffoldState>();

  Future<Map<String, dynamic>>? _profileFuture;
  Future<Map<String, dynamic>>? _statsFuture;
  Future<List<dynamic>>? _activityFuture;
  

  @override
  void initState() {
    super.initState();
    _refreshAll();
  }
//// call services that connect therpaist with users=========================
  void _openConnectionSheet() async {
  final role = (await ApiService.getRole() ?? "user").toLowerCase();
  final userId = await ApiService.getUserId();

  if (!mounted) return;

  if (userId == null || userId.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("No session found. Please login again.")),
    );
    return;
  }

  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
    ),
    builder: (ctx) {
      final codeController = TextEditingController();
      bool loading = false;
      String? myCode;

      Future<void> loadMyCode(StateSetter setModalState) async {
        try {
          setModalState(() => loading = true);
          final code = await ApiService.fetchMyTherapistCode();
          setModalState(() {
            myCode = code;
            loading = false;
          });
        } catch (e) {
          setModalState(() => loading = false);
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text("Failed to load code: $e")),
            );
          }
        }
      }

      Future<void> regenerate(StateSetter setModalState) async {
        try {
          setModalState(() => loading = true);
          final code = await ApiService.regenerateTherapistCode();
          setModalState(() {
            myCode = code;
            loading = false;
          });
        } catch (e) {
          setModalState(() => loading = false);
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text("Failed to regenerate code: $e")),
            );
          }
        }
      }

      Future<void> connect(StateSetter setModalState) async {
        final code = codeController.text.trim();
        if (code.isEmpty) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Please enter a code.")),
          );
          return;
        }

        try {
          setModalState(() => loading = true);
          await ApiService.connectWithCode(patientId: userId, code: code);
          setModalState(() => loading = false);

          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text("Connected successfully ✅")),
            );
          }
          Navigator.of(ctx).pop();
          _refreshAll();
        } catch (e) {
          setModalState(() => loading = false);
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text("Connect failed: $e")),
            );
          }
        }
      }

      return StatefulBuilder(
        builder: (context, setModalState) {
          final isGuardian = role == "therapist" || role == "parent";

          // Lazy-load code when opening for guardian roles
          if (isGuardian && myCode == null && !loading) {
            loadMyCode(setModalState);
          }

          return Padding(
            padding: EdgeInsets.only(
              left: 16,
              right: 16,
              top: 16,
              bottom: MediaQuery.of(context).viewInsets.bottom + 16,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isGuardian ? "Your Connection Code" : "Connect to Therapist/Parent",
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textDark,
                  ),
                ),
                const SizedBox(height: 10),

                if (loading)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 18),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else if (isGuardian) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: AppColors.blue.withOpacity(0.25),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      myCode ?? "—",
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 2,
                        color: AppColors.textDark,
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: (myCode == null || myCode!.isEmpty)
                              ? null
                              : () async {
                                  await Clipboard.setData(ClipboardData(text: myCode!));
                                  if (mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(content: Text("Code copied ✅")),
                                    );
                                  }
                                },
                          icon: const Icon(Icons.copy),
                          label: const Text("Copy"),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => regenerate(setModalState),
                          icon: const Icon(Icons.refresh),
                          label: const Text("Regenerate"),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    "Share this code with your user to connect. (QR can replace this later.)",
                    style: TextStyle(color: AppColors.textDark, fontSize: 12),
                  ),
                ] else ...[
                  TextField(
                    controller: codeController,
                    textCapitalization: TextCapitalization.characters,
                    decoration: InputDecoration(
                      hintText: "Enter code (e.g. G-7K3F9A)",
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () => connect(setModalState),
                      child: const Text("Connect"),
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    "Ask your therapist/parent for their code.",
                    style: TextStyle(color: AppColors.textDark, fontSize: 12),
                  ),
                ],
              ],
            ),
          );
        },
      );
    },
  );
}
//========================================================

  void _refreshAll() {
    _profileFuture = _loadProfile();
    _statsFuture = _loadStats();
    _activityFuture = _loadActivity();
    setState(() {});
  }

  Future<Map<String, dynamic>> _loadProfile() async {
    final userId = await ApiService.getUserId();
    if (userId == null || userId.isEmpty) {
      throw Exception("No user_id found in session. Please login again.");
    }
    return ApiService.fetchMyProfile();
  }

  Future<Map<String, dynamic>> _loadStats() async {
    final userId = await ApiService.getUserId();
    if (userId == null || userId.isEmpty) {
      throw Exception("No user_id found in session. Please login again.");
    }
    return ApiService.fetchProfileStats(userId);
  }

  Future<List<dynamic>> _loadActivity() async {
    final userId = await ApiService.getUserId();
    if (userId == null || userId.isEmpty) {
      throw Exception("No user_id found in session. Please login again.");
    }
    return ApiService.fetchProfileActivity(userId, limit: 10, offset: 0);
  }

  void showLogoutDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return Dialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
          elevation: 0,
          backgroundColor: Colors.transparent,
          child: Container(
            height: 300,
            width: 300,
            decoration: BoxDecoration(
              color: const Color(0xFFFAFCFB),
              borderRadius: BorderRadius.circular(20),
            ),
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                SizedBox(
                  height: 90,
                  child: Stack(
                    alignment: Alignment.bottomCenter,
                    children: [
                      Container(
                        height: 80,
                        width: 80,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: Color(0xFFFAFCFB),
                          image: DecorationImage(
                            image: AssetImage("assets/images/image.jpg"),
                            fit: BoxFit.cover,
                          ),
                        ),
                      )
                    ],
                  ),
                ),
                const SizedBox(height: 10.0),
                const Text(
                  "Are you sure you want to logout?",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Color(0xFF78909C),
                    fontSize: 18.0,
                  ),
                ),
                const SizedBox(height: 10.0),
                Expanded(
                  child: TextButton(
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                    ),
                    onPressed: () async {
                      await ApiService.logout();

                      if (!mounted) return;

                      Navigator.of(context).pushAndRemoveUntil(
                        MaterialPageRoute(builder: (_) => const RoleGate()),
                        (route) => false,
                      );
                    },
                    child: const Text(
                      "Logout",
                      style: TextStyle(
                        color: Color(0xFF78909C),
                        fontWeight: FontWeight.bold,
                        fontSize: 18.0,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Expanded(
                  child: TextButton(
                    onPressed: () {
                      Navigator.of(context).pop();
                    },
                    child: const Text(
                      "Cancel",
                      style: TextStyle(
                        color: Color(0xFFB7CEDE),
                        fontSize: 18.0,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

void _openEditProfileDialog(Map<String, dynamic> profile) {
  final nameC = TextEditingController(text: (profile["name"] ?? "").toString());
  DateTime? selectedDob;

  final dobC = TextEditingController(
    text: (profile["dob"] ?? "").toString(), // expects "YYYY-MM-DD"
  );

  if (dobC.text.isNotEmpty) {
    try {
      selectedDob = DateTime.parse(dobC.text);
    } catch (_) {}
  }

  final usernameC =
      TextEditingController(text: (profile["username"] ?? "").toString());

  // Email might not be returned by /api/users/{id}. Keep optional in UI.
  final emailC = TextEditingController(text: (profile["email"] ?? "").toString());

  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (ctx) {
      bool loading = false;

      Future<void> save(StateSetter setStateDialog) async {
        final newName = nameC.text.trim();
        final newUsername = usernameC.text.trim();
        final newEmail = emailC.text.trim();



        try {
          setStateDialog(() => loading = true);

          await ApiService.updateMyProfile(
            name: newName.isEmpty ? null : newName,
            dob: dobC.text.trim().isEmpty ? null : dobC.text.trim(),
            username: newUsername.isEmpty ? null : newUsername,
            email: newEmail.isEmpty ? null : newEmail,
          );

          if (!mounted) return;
          Navigator.of(ctx).pop();

          // Reload UI
          _refreshAll();

          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Profile updated ✅")),
          );
        } catch (e) {
          setStateDialog(() => loading = false);
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text("Update failed: $e")),
          );
        }
      }

      return StatefulBuilder(
        builder: (context, setStateDialog) {
          return AlertDialog(
            title: const Text("Edit Profile", 
            style: TextStyle(
              color: AppColors.titletext
            ),),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: nameC,
                    decoration: const InputDecoration(labelText: "Name",
                     labelStyle: const TextStyle(
                        color: AppColors.titletext, 
                      ),),
                    style: TextStyle(
                       color: AppColors.textDark
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
  controller: dobC,
  readOnly: true,
  decoration: const InputDecoration(
    labelText: "Date of Birth",
    labelStyle: TextStyle(color: AppColors.titletext),
  ),
  style: TextStyle(color: AppColors.textDark),
  onTap: () async {
    final now = DateTime.now();
    final initial = selectedDob ?? DateTime(now.year - 13, now.month, now.day);

    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(1900, 1, 1),
      lastDate: now,
    );

    if (picked != null) {
      selectedDob = picked;
      final yyyy = picked.year.toString().padLeft(4, '0');
      final mm = picked.month.toString().padLeft(2, '0');
      final dd = picked.day.toString().padLeft(2, '0');
      dobC.text = "$yyyy-$mm-$dd";
      setStateDialog(() {});
    }
  },
),

                  const SizedBox(height: 10),
                  TextField(
                    controller: usernameC,
                    decoration: const InputDecoration(labelText: "Username",
                     labelStyle: const TextStyle(
                        color: AppColors.titletext, 
                      ),
                    ),
                    style: TextStyle(
                       color: AppColors.textDark
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: emailC,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(
                      labelText: "Email",
                       labelStyle: const TextStyle(
                        color: AppColors.titletext, 
                      ),
                    ),
                    style: TextStyle(
                       color: AppColors.textDark
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: loading ? null : () => Navigator.of(ctx).pop(),
                child: const Text("Cancel"),
              ),
              ElevatedButton(
                onPressed: loading ? null : () => save(setStateDialog),
                child: loading
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text("Save"),
              ),
            ],
          );
        },
      );
    },
  );
}

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _profileScaffoldKey,
      backgroundColor: AppColors.background,
      endDrawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: const BoxDecoration(color: AppColors.lighterblue),
              child: const Text(
                'Menu',
                style: TextStyle(
                  color: AppColors.background,
                  fontSize: 24,
                ),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.settings),
              title: const Text('Settings'),
              onTap: () {},
            ),
            ListTile(
                leading: const Icon(Icons.dashboard),
                title: const Text('Dashboard'),
                onTap: () async {
                  Navigator.of(context).pop(); // close drawer

                  final userId = await ApiService.getUserId();
                  if (userId == null || userId.isEmpty) return;

                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => DashboardInsightsScreen(
                        userId: userId,
                      ),
                    ),
                  );
                },
              ),

            ListTile(
              leading: const Icon(Icons.link),
              title: const Text('Connection'),
              onTap: () {
              Navigator.of(context).pop(); // close drawer
              _openConnectionSheet();
            },
            ),
            ListTile(
              leading: const Icon(Icons.logout),
              title: const Text('Logout'),
              onTap: () {
                Navigator.of(context).pop();
                showLogoutDialog(context);
              },
            ),
            ListTile(
              leading: const Icon(Icons.close),
              title: const Text('Close'),
              onTap: () => Navigator.of(context).pop(),
            ),
          ],
        ),
      ),
      body: SafeArea(
        child: FutureBuilder<Map<String, dynamic>>(
          future: _profileFuture,
          builder: (context, profileSnap) {
            if (profileSnap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }

            if (profileSnap.hasError) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(
                    "Failed to load profile:\n${profileSnap.error}",
                    style: const TextStyle(color: AppColors.textDark),
                    textAlign: TextAlign.center,
                  ),
                ),
              );
            }

            final p = profileSnap.data ?? {};
            final name = (p["name"] ?? "Unknown").toString();
            final description = (p["description"] ?? "").toString();

            return RefreshIndicator(
              onRefresh: () async {
                _refreshAll();
              },
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    // Top bar
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            "Profile",
                            style: TextStyle(
                              fontSize: 20,
                              color: AppColors.titletext,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.menu, color: AppColors.lighterblue),
                            onPressed: () {
                              _profileScaffoldKey.currentState?.openEndDrawer();
                            },
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 20),

                    // Avatar
                    const CircleAvatar(
                      radius: 55,
                      backgroundColor: AppColors.blue,
                      child: Icon(
                        Icons.person,
                        size: 55,
                        color: AppColors.lighterblue,
                      ),
                    ),

                    const SizedBox(height: 15),

                    // Name from DB
                      Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        name,
                        style: const TextStyle(
                          fontSize: 22,
                          color: AppColors.textDark,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(width: 6),
                      IconButton(
                        icon: const Icon(Icons.edit, color: AppColors.lighterblue, size: 20),
                        onPressed: () => _openEditProfileDialog(p),
                        tooltip: "Edit profile",
                      ),
                    ],
                  ),

                    const SizedBox(height: 5),

                    // Bio from DB
                    if (description.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 40),
                        child: Text(
                          description,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            color: AppColors.textDark,
                            fontSize: 13,
                          ),
                        ),
                      ),

                    const SizedBox(height: 20),

                    // Stats box (from /api/profile/stats)
                    FutureBuilder<Map<String, dynamic>>(
                      future: _statsFuture,
                      builder: (context, statsSnap) {
                        if (statsSnap.connectionState == ConnectionState.waiting) {
                          return const Padding(
                            padding: EdgeInsets.all(20),
                            child: Center(child: CircularProgressIndicator()),
                          );
                        }

                        if (statsSnap.hasError) {
                          return Padding(
                            padding: const EdgeInsets.all(16),
                            child: Text(
                              "Failed to load stats:\n${statsSnap.error}",
                              style: const TextStyle(color: AppColors.textDark),
                              textAlign: TextAlign.center,
                            ),
                          );
                        }

                        final stats = statsSnap.data ?? {};
                        final streak = (stats["streak"] ?? 0).toString();
                        final activities = (stats["activities"] ?? 0).toString();
                        final connections = (stats["connections"] ?? 0).toString();

                        return Container(
                          margin: const EdgeInsets.symmetric(horizontal: 20),
                          padding: const EdgeInsets.symmetric(vertical: 25),
                          decoration: BoxDecoration(
                            color: AppColors.blue,
                            borderRadius: BorderRadius.circular(15),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: [
                              _buildStat(streak, "Days streak"),
                              _buildDivider(),
                              _buildStat(activities, "Activities"),
                              _buildDivider(),
                              _buildStat(connections, "Connections"),
                            ],
                          ),
                        );
                      },
                    ),

                    const SizedBox(height: 25),

                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 20),
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          "Recent Activity",
                          style: TextStyle(
                            color: AppColors.textDark,
                            fontSize: 18,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 8),

                    // Activity feed (from /api/profile/activity)
                    FutureBuilder<List<dynamic>>(
                      future: _activityFuture,
                      builder: (context, actSnap) {
                        if (actSnap.connectionState == ConnectionState.waiting) {
                          return const Padding(
                            padding: EdgeInsets.all(20),
                            child: Center(child: CircularProgressIndicator()),
                          );
                        }

                        if (actSnap.hasError) {
                          return Padding(
                            padding: const EdgeInsets.all(16),
                            child: Text(
                              "Failed to load activity:\n${actSnap.error}",
                              style: const TextStyle(color: AppColors.textDark),
                              textAlign: TextAlign.center,
                            ),
                          );
                        }

                        final items = actSnap.data ?? [];
                        if (items.isEmpty) {
                          return const Padding(
                            padding: EdgeInsets.all(16),
                            child: Text(
                              "No recent activity yet.",
                              style: TextStyle(color: AppColors.textDark),
                            ),
                          );
                        }

                        return Column(
                          children: items.map((it) {
                            final title = (it["title"] ?? "").toString();
                            final subtitle = (it["subtitle"] ?? "").toString();
                            return _activityTile(title, subtitle.isEmpty ? " " : subtitle);
                          }).toList(),
                        );
                      },
                    ),

                    const SizedBox(height: 40),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildStat(String value, String label) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(
            fontSize: 20,
            color: AppColors.textDark,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(fontSize: 14, color: AppColors.textDark),
        ),
      ],
    );
  }

  Widget _buildDivider() {
    return Container(
      height: 30,
      width: 1,
      color: AppColors.textDark,
    );
  }

  Widget _activityTile(String title, String subtitle) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.blue.withOpacity(0.3),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: AppColors.textDark,
              fontSize: 16,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: const TextStyle(
              color: AppColors.textDark,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}




// import 'package:flutter/material.dart';
// import 'package:flutter_application_1/services/api_service.dart';
// import '../../theme/app_colors.dart';
// import 'dashboard.dart';
// import '../../role_gate.dart';

// class ProfileScreen extends StatefulWidget {
//   const ProfileScreen({super.key});

//   @override
//   State<ProfileScreen> createState() => _ProfileScreenState();
// }

// class _ProfileScreenState extends State<ProfileScreen> {
//   final GlobalKey<ScaffoldState> _profileScaffoldKey = GlobalKey<ScaffoldState>();

//   Future<Map<String, dynamic>>? _profileFuture;

//   @override
//   void initState() {
//     super.initState();
//     _profileFuture = _loadProfile();
//   }

//   Future<Map<String, dynamic>> _loadProfile() async {
//     final userId = await ApiService.getUserId();
//     if (userId == null || userId.isEmpty) {
//       throw Exception("No user_id found in session. Please login again.");
//     }
//     return ApiService.fetchUserProfile(userId);
//   }

//   void showLogoutDialog(BuildContext context) {
//     showDialog(
//       context: context,
//       builder: (BuildContext context) {
//         return Dialog(
//           shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
//           elevation: 0,
//           backgroundColor: Colors.transparent,
//           child: Container(
//             height: 300,
//             width: 300,
//             decoration: BoxDecoration(
//               color: const Color(0xFFFAFCFB),
//               borderRadius: BorderRadius.circular(20),
//             ),
//             padding: const EdgeInsets.all(24),
//             child: Column(
//               mainAxisAlignment: MainAxisAlignment.center,
//               children: [
//                 SizedBox(
//                   height: 90,
//                   child: Stack(
//                     alignment: Alignment.bottomCenter,
//                     children: [
//                       Container(
//                         height: 80,
//                         width: 80,
//                         decoration: const BoxDecoration(
//                           shape: BoxShape.circle,
//                           color: Color(0xFFFAFCFB),
//                           image: DecorationImage(
//                             image: AssetImage("assets/images/image.jpg"),
//                             fit: BoxFit.cover,
//                           ),
//                         ),
//                       )
//                     ],
//                   ),
//                 ),
//                 const SizedBox(height: 10.0),
//                 const Text(
//                   "Are you sure you want to logout?",
//                   textAlign: TextAlign.center,
//                   style: TextStyle(
//                     color: Color(0xFF78909C),
//                     fontSize: 18.0,
//                   ),
//                 ),
//                 const SizedBox(height: 10.0),
//                 Expanded(
//                   child: TextButton(
//                     style: TextButton.styleFrom(
//                       padding: const EdgeInsets.symmetric(horizontal: 10),
//                     ),
//                     onPressed: () async {
//                       await ApiService.logout(); // ✅ use the correct one

//                       if (!mounted) return;

//                       Navigator.of(context).pushAndRemoveUntil(
//                         MaterialPageRoute(builder: (_) => const RoleGate()),
//                         (route) => false,
//                       );
//                     },
//                     child: const Text(
//                       "Logout",
//                       style: TextStyle(
//                         color: Color(0xFF78909C),
//                         fontWeight: FontWeight.bold,
//                         fontSize: 18.0,
//                       ),
//                     ),
//                   ),
//                 ),
//                 const SizedBox(height: 10),
//                 Expanded(
//                   child: TextButton(
//                     onPressed: () {
//                       Navigator.of(context).pop();
//                     },
//                     child: const Text(
//                       "Cancel",
//                       style: TextStyle(
//                         color: Color(0xFFB7CEDE),
//                         fontSize: 18.0,
//                       ),
//                     ),
//                   ),
//                 ),
//               ],
//             ),
//           ),
//         );
//       },
//     );
//   }

//   @override
//   Widget build(BuildContext context) {
//     return Scaffold(
//       key: _profileScaffoldKey,
//       backgroundColor: AppColors.background,

//       endDrawer: Drawer(
//         child: ListView(
//           padding: EdgeInsets.zero,
//           children: [
//             DrawerHeader(
//               decoration: const BoxDecoration(color: AppColors.lighterblue),
//               child: const Text(
//                 'Menu',
//                 style: TextStyle(
//                   color: AppColors.background,
//                   fontSize: 24,
//                 ),
//               ),
//             ),
//             ListTile(
//               leading: const Icon(Icons.settings),
//               title: const Text('Settings'),
//               onTap: () {},
//             ),
//             ListTile(
//               leading: const Icon(Icons.dashboard),
//               title: const Text('Dashboard'),
//               onTap: () {
//                 Navigator.push(
//                   context,
//                   MaterialPageRoute(builder: (context) => const DashboardInsightsScreen()),
//                 );
//               },
//             ),
//             ListTile(
//               leading: const Icon(Icons.help),
//               title: const Text('Help & Support'),
//               onTap: () {},
//             ),
//             ListTile(
//               leading: const Icon(Icons.logout),
//               title: const Text('Logout'),
//               onTap: () {
//                 Navigator.of(context).pop();
//                 showLogoutDialog(context);
//               },
//             ),
//             ListTile(
//               leading: const Icon(Icons.close),
//               title: const Text('Close'),
//               onTap: () => Navigator.of(context).pop(),
//             ),
//           ],
//         ),
//       ),

//       body: SafeArea(
//         child: FutureBuilder<Map<String, dynamic>>(
//           future: _profileFuture,
//           builder: (context, snapshot) {
//             if (snapshot.connectionState == ConnectionState.waiting) {
//               return const Center(
//                 child: CircularProgressIndicator(),
//               );
//             }

//             if (snapshot.hasError) {
//               return Center(
//                 child: Padding(
//                   padding: const EdgeInsets.all(16),
//                   child: Text(
//                     "Failed to load profile:\n${snapshot.error}",
//                     style: const TextStyle(color: AppColors.textDark),
//                     textAlign: TextAlign.center,
//                   ),
//                 ),
//               );
//             }

//             final p = snapshot.data ?? {};
//             final name = (p["name"] ?? "Unknown").toString();
//             final description = (p["description"] ?? "").toString();
//             final streak = (p["streak"] ?? 0).toString();
//             final connections = (p["connections"] ?? 0).toString();

//             return SingleChildScrollView(
//               child: Column(
//                 crossAxisAlignment: CrossAxisAlignment.center,
//                 children: [
//                   // Top bar
//                   Padding(
//                     padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
//                     child: Row(
//                       mainAxisAlignment: MainAxisAlignment.spaceBetween,
//                       children: [
//                         const Text(
//                           "Profile",
//                           style: TextStyle(
//                             fontSize: 20,
//                             color: AppColors.titletext,
//                             fontWeight: FontWeight.w500,
//                           ),
//                         ),
//                         IconButton(
//                           icon: const Icon(Icons.menu, color: AppColors.lighterblue),
//                           onPressed: () {
//                             _profileScaffoldKey.currentState?.openEndDrawer();
//                           },
//                         ),
//                       ],
//                     ),
//                   ),

//                   const SizedBox(height: 20),

//                   // Avatar (keep yours; later you can use p["photo"] if you store image URLs)
//                   const CircleAvatar(
//                     radius: 55,
//                     backgroundColor: AppColors.blue,
//                     child: Icon(
//                       Icons.person,
//                       size: 55,
//                       color: AppColors.lighterblue,
//                     ),
//                   ),

//                   const SizedBox(height: 15),

//                   // Name from DB
//                   Text(
//                     name,
//                     style: const TextStyle(
//                       fontSize: 22,
//                       color: AppColors.textDark,
//                       fontWeight: FontWeight.w600,
//                     ),
//                   ),

//                   const SizedBox(height: 5),

//                   // Bio from DB
//                   if (description.isNotEmpty)
//                     Padding(
//                       padding: const EdgeInsets.symmetric(horizontal: 40),
//                       child: Text(
//                         description,
//                         textAlign: TextAlign.center,
//                         style: const TextStyle(
//                           color: AppColors.textDark,
//                           fontSize: 13,
//                         ),
//                       ),
//                     ),

//                   const SizedBox(height: 20),

//                   // Stats box (some from DB, keep the rest as placeholder)
//                   Container(
//                     margin: const EdgeInsets.symmetric(horizontal: 20),
//                     padding: const EdgeInsets.symmetric(vertical: 25),
//                     decoration: BoxDecoration(
//                       color: AppColors.blue,
//                       borderRadius: BorderRadius.circular(15),
//                     ),
//                     child: Row(
//                       mainAxisAlignment: MainAxisAlignment.spaceEvenly,
//                       children: [
//                         _buildStat(streak, "Days streak"),
//                         _buildDivider(),
//                         _buildStat("128", "Activities"), // keep until you add an endpoint for this
//                         _buildDivider(),
//                         _buildStat(connections, "Connections"),
//                       ],
//                     ),
//                   ),

//                   const SizedBox(height: 25),

//                   const Padding(
//                     padding: EdgeInsets.symmetric(horizontal: 20),
//                     child: Align(
//                       alignment: Alignment.centerLeft,
//                       child: Text(
//                         "Recent Activity",
//                         style: TextStyle(
//                           color: AppColors.textDark,
//                           fontSize: 18,
//                           fontWeight: FontWeight.w500,
//                         ),
//                       ),
//                     ),
//                   ),

//                   const SizedBox(height: 8),

//                   _activityTile("Completed daily check-in", "Today, 9:30 AM"),
//                   _activityTile("Played Emotion Charades", "Yesterday, 7:15 PM"),
//                   _activityTile("Posted in Community", "Yesterday, 2:45 PM"),
//                   _activityTile("Chat with Wellness Agent", "2 days ago"),

//                   const SizedBox(height: 40),
//                 ],
//               ),
//             );
//           },
//         ),
//       ),
//     );
//   }

//   Widget _buildStat(String value, String label) {
//     return Column(
//       children: [
//         Text(
//           value,
//           style: const TextStyle(
//             fontSize: 20,
//             color: AppColors.textDark,
//             fontWeight: FontWeight.w600,
//           ),
//         ),
//         const SizedBox(height: 4),
//         Text(
//           label,
//           style: const TextStyle(fontSize: 14, color: AppColors.textDark),
//         ),
//       ],
//     );
//   }

//   Widget _buildDivider() {
//     return Container(
//       height: 30,
//       width: 1,
//       color: AppColors.textDark,
//     );
//   }

//   Widget _activityTile(String title, String subtitle) {
//     return Container(
//       width: double.infinity,
//       margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
//       padding: const EdgeInsets.all(18),
//       decoration: BoxDecoration(
//         color: AppColors.blue.withOpacity(0.3),
//         borderRadius: BorderRadius.circular(14),
//       ),
//       child: Column(
//         crossAxisAlignment: CrossAxisAlignment.start,
//         children: [
//           Text(
//             title,
//             style: const TextStyle(
//               color: AppColors.textDark,
//               fontSize: 16,
//               fontWeight: FontWeight.w500,
//             ),
//           ),
//           const SizedBox(height: 4),
//           Text(
//             subtitle,
//             style: const TextStyle(
//               color: AppColors.textDark,
//               fontSize: 12,
//             ),
//           ),
//         ],
//       ),
//     );
//   }
// }
