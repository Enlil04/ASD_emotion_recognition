import 'package:flutter/material.dart';
import '/../theme/app_colors.dart'; // Ensure this import matches your project structure

// ---------------------------------------------------------
// 1. DATA MODELS (To structure your data)
// ---------------------------------------------------------
class ConnectedUser {
  final String name;
  final String lastNotification;
  final String lastActive;
  final Color avatarColor;
  final List<ActivityDetection> weeklyActivity;

  ConnectedUser({
    required this.name,
    required this.lastNotification,
    required this.lastActive,
    required this.avatarColor,
    required this.weeklyActivity,
  });
}

class ActivityDetection {
  final String label;
  final String date;
  final String time;
  final Color color;

  ActivityDetection({
    required this.label,
    required this.date,
    required this.time,
    required this.color,
  });
}

// ---------------------------------------------------------
// 2. USERS SCREEN (The List)
// ---------------------------------------------------------
class UsersScreen extends StatelessWidget {
  UsersScreen({super.key});

  // Mock Data
  final List<ConnectedUser> users = [
    ConnectedUser(
      name: "Alex",
      lastNotification: "High stress detected during homework",
      lastActive: "2 mins ago",
      avatarColor: Colors.blueAccent,
      weeklyActivity: [
        ActivityDetection(label: "High Stress", date: "Today", time: "4:30 PM", color: Colors.redAccent),
        ActivityDetection(label: "Focused", date: "Yesterday", time: "2:00 PM", color: Colors.blue),
        ActivityDetection(label: "Happy", date: "Mon", time: "10:00 AM", color: Colors.green),
      ],
    ),
    ConnectedUser(
      name: "Sarah",
      lastNotification: "Completed daily check-in",
      lastActive: "1 hour ago",
      avatarColor: Colors.orangeAccent,
      weeklyActivity: [
        ActivityDetection(label: "Calm", date: "Today", time: "9:00 AM", color: Colors.purple),
        ActivityDetection(label: "Happy", date: "Yesterday", time: "6:15 PM", color: Colors.green),
      ],
    ),
  ];

  @override
  Widget build(BuildContext context) {
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
      ),
      body: SafeArea(
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: users.length,
          itemBuilder: (context, index) {
            final user = users[index];
            return _buildUserTile(context, user);
          },
        ),
      ),
    );
  }

  Widget _buildUserTile(BuildContext context, ConnectedUser user) {
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
        onTap: () {
          // Navigate to details
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => UserDetailScreen(user: user),
            ),
          );
        },
        // 1. ICON (Avatar)
        leading: CircleAvatar(
          radius: 28,
          backgroundColor: user.avatarColor.withOpacity(0.2),
          child: Text(
            user.name[0], // First letter of name
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: user.avatarColor,
            ),
          ),
        ),
        // 2. NAME & LAST ACTIVE
        title: Padding(
          padding: const EdgeInsets.only(bottom: 6.0),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                user.name,
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 18,
                  color: AppColors.textDark,
                ),
              ),
              Text(
                user.lastActive,
                style: TextStyle(fontSize: 12, color: Colors.grey[400]),
              ),
            ],
          ),
        ),
        // 3. LAST RECEIVED NOTIFICATION
        subtitle: Row(
          children: [
            const Icon(Icons.notifications_none, size: 16, color: Colors.grey),
            const SizedBox(width: 5),
            Expanded(
              child: Text(
                user.lastNotification,
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
}

// ---------------------------------------------------------
// 3. USER DETAIL SCREEN (The Weekly Report)
// ---------------------------------------------------------
class UserDetailScreen extends StatelessWidget {
  final ConnectedUser user;

  const UserDetailScreen({super.key, required this.user});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(
          "${user.name}'s Report",
          style: const TextStyle(color: AppColors.textDark),
        ),
        backgroundColor: AppColors.background,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppColors.textDark),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Profile
            Center(
              child: Column(
                children: [
                  CircleAvatar(
                    radius: 40,
                    backgroundColor: user.avatarColor.withOpacity(0.2),
                    child: Text(
                      user.name[0],
                      style: TextStyle(fontSize: 40, color: user.avatarColor, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    user.name,
                    style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.textDark),
                  ),
                  Text(
                    "Connected",
                    style: TextStyle(color: Colors.green[600], fontWeight: FontWeight.w500),
                  )
                ],
              ),
            ),
            
            const SizedBox(height: 30),
            
            // Section Title
            const Text(
              "Last Week's Activity",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textDark),
            ),
            
            const SizedBox(height: 15),

            // Activity List
            ...user.weeklyActivity.map((activity) => _buildActivityRow(activity)),
            
            // Empty state check
            if (user.weeklyActivity.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 20),
                child: Center(child: Text("No activity recorded last week.")),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildActivityRow(ActivityDetection activity) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.blue.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: activity.color.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.show_chart, color: activity.color, size: 20),
          ),
          const SizedBox(width: 15),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  activity.label,
                  style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.textDark),
                ),
                Text(
                  "Detected via Camera",
                  style: TextStyle(fontSize: 12, color: Colors.grey[500]),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                activity.date,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.textDark),
              ),
              Text(
                activity.time,
                style: TextStyle(fontSize: 12, color: Colors.grey[500]),
              ),
            ],
          )
        ],
      ),
    );
  }
}