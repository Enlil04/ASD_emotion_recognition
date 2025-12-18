import 'package:flutter/material.dart';

// Core
import '../../theme/app_colors.dart';
// MODEL IMPORT (This is where UserRole comes from)
import '../../user_role.dart'; // Make sure this path points to your file!


// Screens
import 'profile_screen.dart';
import 'community/community_screen.dart';
import 'camera_screen.dart';
import 'nimi_screen.dart';
import 'games_screen.dart';

// Parent Screens
import '../parent/users_screen.dart'; 

// --- DELETE THE "enum UserRole" LINES THAT WERE HERE ---

class MainScaffold extends StatefulWidget {
  final UserRole userRole;

  // Default to child if nothing is passed
  const MainScaffold({super.key, this.userRole = UserRole.individual});

  @override
  State<MainScaffold> createState() => _MainScaffoldState();
}

class _MainScaffoldState extends State<MainScaffold> {
  int _selectedIndex = 2; // Start at Nimi

  @override
  Widget build(BuildContext context) {
    
    // 1. DYNAMIC PAGES
    final List<Widget> pages = [
      GamesScreen(), // Index 0
      
      // Index 1: The Role Swap
      widget.userRole == UserRole.guardian 
          ? UsersScreen() 
          : const CameraScreen(),
          
      const NimiScreen(), // Index 2
      
      // Index 3: Pass role to Community
      CommunityScreen(userRole: widget.userRole), 
      
      ProfileScreen(), // Index 4
    ];

    // 2. DYNAMIC ICONS
    final List<BottomNavigationBarItem> navItems = [
      const BottomNavigationBarItem(
        icon: Icon(Icons.videogame_asset),
        label: "Games",
      ),
      
      // Index 1: The Icon Swap
      widget.userRole == UserRole.guardian
          ? const BottomNavigationBarItem(
              icon: Icon(Icons.people),
              label: "Connected",
            )
          : const BottomNavigationBarItem(
              icon: Icon(Icons.camera_alt),
              label: "Camera",
            ),
            
      const BottomNavigationBarItem(
        icon: Icon(Icons.bubble_chart),
        label: "Nimi",
      ),
      const BottomNavigationBarItem(
        icon: Icon(Icons.public),
        label: "Community",
      ),
      const BottomNavigationBarItem(
        icon: Icon(Icons.person),
        label: "Profile",
      ),
    ];

    return Scaffold(
      body: pages[_selectedIndex],

      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        currentIndex: _selectedIndex,
        onTap: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        selectedItemColor: AppColors.textDark,
        unselectedItemColor: AppColors.lighterblue,
        backgroundColor: AppColors.background,
        items: navItems,
      ),
    );
  }
}