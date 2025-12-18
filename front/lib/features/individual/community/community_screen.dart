import 'package:flutter/material.dart';
import '../../../theme/app_colors.dart';
import 'chat_screen.dart';
import 'package:flutter_application_1/user_role.dart';

class CommunityScreen extends StatelessWidget {
  const CommunityScreen({super.key, required this.userRole});
  final UserRole userRole;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,

      appBar: AppBar(
        title: const Text(
          'Community',
          style: TextStyle(
            color: AppColors.titletext,
            fontWeight: FontWeight.w500,
            fontSize: 20,
          ),
        ),
        backgroundColor: AppColors.background,
        elevation: 0,
        automaticallyImplyLeading: false,
        // --- LOGIC FIX HERE ---
        actions: [
          // Only show this button if the user is NOT a parent
          if (userRole != UserRole.guardian) 
            IconButton(
              icon: const Icon(Icons.messenger, color: AppColors.lighterblue),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    // Make sure this matches your actual file/class name
                    builder: (context) => const MessagesScreen(), 
                  ),
                );
              },
            ),
            
          const SizedBox(width: 10),
        ],
      ),

      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // Search
            TextField(
              decoration: InputDecoration(
                hintText: "Search topics...",
                hintStyle: const TextStyle(color: AppColors.lighterblue),
                prefixIcon: const Icon(Icons.search, color: AppColors.blue),
                filled: true,
                fillColor: AppColors.blue.withOpacity(0.3),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Example post
            const CommunityPostCard(
              author: "Mindfulness Coach",
              time: "2 hours ago",
              content:
                  "Reminder 🌱\n\nTake a slow breath in through your nose, "
                  "hold for 4 seconds, and gently release.\n\n"
                  "You’re doing better than you think.",
              likes: 24,
              comments: 5,
            ),
          ],
        ),
      ),
    );
  }
}

class CommunityPostCard extends StatelessWidget {
  final String author;
  final String time;
  final String content;
  final int likes;
  final int comments;

  const CommunityPostCard({
    super.key,
    required this.author,
    required this.time,
    required this.content,
    required this.likes,
    required this.comments,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.blue.withOpacity(0.25),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              CircleAvatar(
                radius: 18,
                backgroundColor: AppColors.lighterblue,
                child: Text(
                  author[0],
                  style: const TextStyle(
                    color: AppColors.background,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    author,
                    style: const TextStyle(
                      color: AppColors.textDark,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    time,
                    style: TextStyle(
                      color: AppColors.textDark.withOpacity(0.6),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ],
          ),

          const SizedBox(height: 12),

          // Content
          Text(
            content,
            style: const TextStyle(
              color: AppColors.textDark,
              fontSize: 14,
              height: 1.4,
            ),
          ),

          const SizedBox(height: 12),

          // Actions
          Row(
            children: [
              Icon(Icons.favorite_border,
                  size: 18, color: AppColors.lighterblue),
              const SizedBox(width: 4),
              Text("$likes",
                  style: const TextStyle(color: AppColors.textDark)),
              const SizedBox(width: 16),
              Icon(Icons.chat_bubble_outline,
                  size: 18, color: AppColors.lighterblue),
              const SizedBox(width: 4),
              Text("$comments",
                  style: const TextStyle(color: AppColors.textDark)),
            ],
          ),
        ],
      ),
    );
  }
}
