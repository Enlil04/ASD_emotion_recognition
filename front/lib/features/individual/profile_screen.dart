import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import 'dashboard.dart';

class ProfileScreen extends StatelessWidget {
  // We keep the GlobalKey here because this specific screen has a specific Drawer
  final GlobalKey<ScaffoldState> _profileScaffoldKey = GlobalKey<ScaffoldState>();

  ProfileScreen({super.key});

  // ---------------------------------------------------------------------------
  // 1. ADD YOUR DIALOG FUNCTION HERE (Inside the class)
  // ---------------------------------------------------------------------------
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
                            // Ensure this asset exists in your pubspec.yaml
                            image: AssetImage("assets/image2.png"),
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
                        padding: const EdgeInsets.symmetric(horizontal: 10)),
                    onPressed: () {
                      // --- ADD YOUR LOGOUT LOGIC HERE ---
                      print("User logged out");
                      Navigator.of(context).pop(); // Close dialog
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
                      Navigator.of(context).pop(); // Close dialog
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
              decoration: const BoxDecoration(
                color: AppColors.lighterblue,
              ),
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
              onTap: () {
                Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => const DashboardInsightsScreen()),
                  );
              },  
            ),
            ListTile(
              leading: const Icon(Icons.help),
              title: const Text('Help & Support'),
              onTap: () {},
            ),
            
            // -----------------------------------------------------------------
            // 2. CONNECT THE FUNCTION TO THE LOGOUT BUTTON
            // -----------------------------------------------------------------
            ListTile(
              leading: const Icon(Icons.logout),
              title: const Text('Logout'),
              onTap: () {
                Navigator.of(context).pop(); // Close the drawer first
                showLogoutDialog(context);   // Open your custom dialog
              },
            ),
            
            ListTile(
              leading: const Icon(Icons.close),
              title: const Text('Close'),
              onTap: () {
                Navigator.of(context).pop();
              },
            ),
          ],
        ),
      ),

      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Top bar
              Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
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
                      icon: const Icon(Icons.menu,
                          color: AppColors.lighterblue),
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
              // Name
              const Text(
                "Alex Morgan",
                style: TextStyle(
                  fontSize: 22,
                  color: AppColors.textDark,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 5),
              // Bio
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 40),
                child: Text(
                  "Exploring emotions and building emotional intelligence through mindfulness",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: AppColors.textDark,
                    fontSize: 13,
                  ),
                ),
              ),
              const SizedBox(height: 20),
              // Stats box
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 20),
                padding: const EdgeInsets.symmetric(vertical: 25),
                decoration: BoxDecoration(
                  color: AppColors.blue,
                  borderRadius: BorderRadius.circular(15),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _buildStat("42", "Days streak"),
                    _buildDivider(),
                    _buildStat("128", "Activities"),
                    _buildDivider(),
                    _buildStat("15", "Connections"),
                  ],
                ),
              ),
              const SizedBox(height: 25),
              // Recent Activity Title
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
              // Activity cards
              _activityTile("Completed daily check-in", "Today, 9:30 AM"),
              _activityTile("Played Emotion Charades", "Yesterday, 7:15 PM"),
              _activityTile("Posted in Community", "Yesterday, 2:45 PM"),
              _activityTile("Chat with Wellness Agent", "2 days ago"),
              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }

  // Widget for stats
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