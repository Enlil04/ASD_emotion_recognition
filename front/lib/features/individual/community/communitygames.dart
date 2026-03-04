import 'package:flutter/material.dart';
import '../../../theme/app_colors.dart';

class CommunityGamesScreen extends StatelessWidget {
  const CommunityGamesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text(
          'Community Games',
          style: TextStyle(
            color: AppColors.titletext,
            fontWeight: FontWeight.w500,
            fontSize: 20,
          ),
        ),
        backgroundColor: AppColors.background,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppColors.textDark),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Header Text
            const Text(
              "Active Lobbies",
              style: TextStyle(
                color: AppColors.textDark,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 15),

            // Multiplayer Lobbies
            LobbyTile(
              gameName: "Color Match Duel",
              hostName: "Sarah K.",
              playerCount: "1/2 Players",
              isOpen: true,
              onJoin: () {
                // Navigate to game lobby
              },
            ),
            LobbyTile(
              gameName: "Emotion Garden Co-op",
              hostName: "Wellness Agent",
              playerCount: "3/4 Players",
              isOpen: true,
              onJoin: () {
                // Navigate to game lobby
              },
            ),
            LobbyTile(
              gameName: "Memory Card Battle",
              hostName: "Mindfulness Group",
              playerCount: "2/2 Players",
              isOpen: false, // Lobby full
              onJoin: () {},
            ),
            LobbyTile(
              gameName: "Road Connect Race",
              hostName: "Alex J.",
              playerCount: "1/2 Players",
              isOpen: true,
              onJoin: () {
                // Navigate to game lobby
              },
            ),
          ],
        ),
      ),
    );
  }
}

class LobbyTile extends StatelessWidget {
  final String gameName;
  final String hostName;
  final String playerCount;
  final bool isOpen;
  final VoidCallback onJoin;

  const LobbyTile({
    super.key,
    required this.gameName,
    required this.hostName,
    required this.playerCount,
    required this.isOpen,
    required this.onJoin,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isOpen
            ? AppColors.blue.withOpacity(0.35) // Brighter for open lobbies
            : AppColors.blue.withOpacity(0.15), // Dimmed for full lobbies
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          // Game Icon
          CircleAvatar(
            radius: 22,
            backgroundColor: AppColors.lighterblue,
            child: const Icon(
              Icons.sports_esports, // Gamepad icon
              color: AppColors.background,
              size: 24,
            ),
          ),

          const SizedBox(width: 12),

          // Lobby Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  gameName,
                  style: const TextStyle(
                    color: AppColors.textDark,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  "Hosted by $hostName • $playerCount",
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: AppColors.textDark.withOpacity(0.7),
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(width: 8),

          // Join Button / Status
          if (isOpen)
            ElevatedButton(
              onPressed: onJoin,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.lighterblue,
                foregroundColor: AppColors.background,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              ),
              child: const Text(
                "Join",
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
            )
          else
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.background.withOpacity(0.5),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                "Full",
                style: TextStyle(
                  color: AppColors.textDark.withOpacity(0.5),
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
        ],
      ),
    );
  }
}