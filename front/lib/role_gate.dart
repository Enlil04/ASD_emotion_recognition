import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../user_role.dart';          // for UserRole + mapBackendRoleToEnum
import 'auth/login_screen.dart';
import 'features/individual/navigation.dart';

class RoleGate extends StatelessWidget {
  const RoleGate({super.key});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder(
      future: Future.wait([
        ApiService.getToken(),
        ApiService.getRole(),
      ]),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }

        final results = snapshot.data;
        if (results == null) return const LoginPage();

        final token = results[0] as String?;
        final roleStr = results[1] as String?;

        // If no token -> not logged in
        if (token == null || token.isEmpty) {
          return const LoginPage();
        }

        // If role missing, default to individual
        final roleEnum = mapBackendRoleToEnum(roleStr ?? "user");

        // ✅ Always go to the FULL UI
        return MainScaffold(userRole: roleEnum);
      },
    );
  }
}
