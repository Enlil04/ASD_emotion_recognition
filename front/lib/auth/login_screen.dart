import 'package:flutter/material.dart';
import 'package:flutter_application_1/theme/app_colors.dart';

import '../role_gate.dart';
import '../services/api_service.dart';
import 'package:flutter_application_1/auth/signup/role_screen.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _emailC = TextEditingController();
  final _pwC = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _emailC.dispose();
    _pwC.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    final email = _emailC.text.trim();
    final pw = _pwC.text;

    if (email.isEmpty || pw.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Enter email and password.")),
      );
      return;
    }

    setState(() => _loading = true);

    try {
      await ApiService.login(email: email, password: pw);

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const RoleGate()),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.lighterblue,
      body: Column(
        children: [
          // The top title circle
          Container(
            width: double.infinity,
            height: 220,
            decoration: const BoxDecoration(
              color: AppColors.background,
              borderRadius: BorderRadius.only(
                bottomLeft: Radius.circular(200.0),
                bottomRight: Radius.circular(200.0),
              ),
            ),
            child: const Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  "Nimi",
                  style: TextStyle(
                    color: AppColors.textDark,
                    fontWeight: FontWeight.bold,
                    fontSize: 35.0,
                    letterSpacing: 3.0,
                  ),
                ),
              ],
            ),
          ),

          // the actual content
          Expanded(
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 30.0),
                child: Column(
                  children: [
                    const SizedBox(height: 30.0),
                    Column(
                      children: [
                        const Text(
                          "login",
                          style: TextStyle(
                            color: AppColors.textDark,
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 5.0),
                        Container(
                          width: 80,
                          height: 3,
                          color: AppColors.textDark,
                        ),
                        const SizedBox(height: 30.0),
                      ],
                    ),

                    _buildTextField(
                      controller: _emailC,
                      field: "Email address",
                      icon: Icons.person_3_outlined,
                    ),
                    const SizedBox(height: 16.0),

                    _buildTextField(
                      field: "Password",
                      icon: Icons.password,
                      isPassword: true,
                      controller: _pwC,
                    ),
                    const SizedBox(height: 16.0),

                    ElevatedButton(
                      onPressed: _loading ? null : _handleLogin,
                      style: const ButtonStyle(
                        backgroundColor:
                            WidgetStatePropertyAll(AppColors.textDark),
                        padding: WidgetStatePropertyAll(
                          EdgeInsets.symmetric(
                            horizontal: 150.0,
                            vertical: 15.0,
                          ),
                        ),
                      ),
                      child: Text(
                        _loading ? "Logging in..." : "Login",
                        style: const TextStyle(
                          color: AppColors.background,
                          fontWeight: FontWeight.bold,
                          fontSize: 15.0,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16.0),

                    GestureDetector(
                      onTap: () {
                        Navigator.push(context,
                          MaterialPageRoute(builder: (_) => const SignUp()));
                      },
                      child: const Text(
                        "Don't have an account? Sign up",
                        style: TextStyle(
                          color: AppColors.textDark,
                          decoration: TextDecoration.underline,
                          decorationColor: AppColors.textDark,
                        ),
                      ),
                    ),

                    SizedBox(
                      height: 250,
                      child: Stack(
                        alignment: Alignment.bottomCenter,
                        children: [
                          Container(
                            height: 220,
                            width: 220,
                            decoration: const BoxDecoration(
                              shape: BoxShape.circle,
                              color: AppColors.background,
                              image: DecorationImage(
                                image: AssetImage("assets/images/image.jpg"),
                                fit: BoxFit.cover,
                              ),
                            ),
                          )
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

Widget _buildTextField({
  required String field,
  required IconData icon,
  bool isPassword = false,
  TextEditingController? controller,
}) {
  return TextField(
    controller: controller,
    obscureText: isPassword,
    style: const TextStyle(
      color: AppColors.textDark,
    ),
    decoration: InputDecoration(
      filled: true,
      fillColor: AppColors.background,
      hintText: field,
      hintStyle: const TextStyle(
        color: AppColors.textDark,
        fontSize: 14,
      ),
      prefixIcon: Icon(icon, color: AppColors.lighterblue),
      contentPadding: const EdgeInsets.symmetric(vertical: 16.0),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(30),
        borderSide: BorderSide.none,
      ),
    ),
  );
}



// import 'package:flutter/material.dart';
// import 'package:flutter_application_1/theme/app_colors.dart';
// import '../role_gate.dart';
// import '../services/api_service.dart';

// class LoginPage extends StatefulWidget {
//   const LoginPage({super.key});
 
//   @override
//   State<LoginPage> createState() => _LoginPageState();
// }

// class _LoginPageState extends State<LoginPage> {
  
//   final _emailC = TextEditingController();
//   final _pwC = TextEditingController();
//   bool _loading = false;

//   @override
//   void dispose() {
//     _emailC.dispose();
//     _pwC.dispose();
//     super.dispose();
//   }

//   @override
//   Widget build(BuildContext context) {
//     return const Login();
//   }
// }

// class Login extends StatelessWidget {
//   const Login({super.key,});

//   @override
//   Widget build(BuildContext context) {
//     return Scaffold(
//       backgroundColor: AppColors.lighterblue,
//       body: Column(
    
//       children:[
//         //The top title circle
//         Container(
//           width: double.infinity,
//           height: 220,
//           decoration: BoxDecoration(
//             color: AppColors.background,
//             borderRadius: BorderRadius.only(
//               bottomLeft: Radius.circular(200.0),
//               bottomRight: Radius.circular(200.0)
//             ), 
//           ),
//           child: Column(
//             mainAxisAlignment: MainAxisAlignment.center,
//             children: [
//               Text("Nimi",
//               style: TextStyle(
//                 color: AppColors.textDark,
//                 fontWeight: FontWeight.bold,
//                 fontSize: 35.0,
//                 letterSpacing: 3.0
//               ),),
//             ],
//           ),
    
//         ),
    
//         //the actual content
//         Expanded(
//           child: SingleChildScrollView(
//             physics: const BouncingScrollPhysics(),
//             child: Padding(
//               padding: const EdgeInsets.symmetric(horizontal:30.0 ),
//               child: Column(
//                 children: [
//                   SizedBox(height: 30.0,),
//                   Column(
//                     children: [
//                       Text("login",
//                       style: TextStyle(
//                         color: AppColors.textDark,
//                         fontSize: 24,
//                         fontWeight: FontWeight.bold
//                       ),),
//                       SizedBox(height: 5.0,),
//                      Container(
//                       width: 80,
//                       height: 3,
//                       color: AppColors.textDark,
//                      ),
//                       SizedBox(height: 30.0,)
//                     ],
//                   ),
//                   _buildTextField(
//                     controller: _emailC,
//                     field: "Email address",
//                     icon: Icons.person_3_outlined,
//                   ),
//                   SizedBox(height: 16.0,),
//                   _buildTextField(field: "Password", icon: Icons.password, isPassword: true, controller: _pwC,),
//                    SizedBox(height: 16.0,),
                  
//                    ElevatedButton(
//                   onPressed: (){}, 
//                   child: Text("Login",
//                   style: TextStyle(
//                     color: AppColors.background,
//                     fontWeight: FontWeight.bold,
//                     fontSize: 15.0
//                   ),),
//                   style: ButtonStyle(
//                     backgroundColor: WidgetStatePropertyAll(AppColors.textDark),
//                     padding: WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: 150.0, vertical: 15.0))
//                   ),),
//                     SizedBox(height: 16.0,),
                 
//                   GestureDetector(
//                     onTap: (){},
//                     child: Text("Don't have an account? Sign up",
//                     style: TextStyle(
//                       color: AppColors.textDark,
//                       decoration: TextDecoration.underline,
//                       decorationColor: AppColors.textDark

//                     ),),
//                   ), 
//                   SizedBox(
//                     height: 250,
//                     child: Stack(
//                       alignment: Alignment.bottomCenter,
//                       children: [
//                         Container(
//                           height: 220,
//                           width: 220,
//                           decoration: BoxDecoration(
//                             shape: BoxShape.circle,
//                             color: AppColors.background,
//                             image: DecorationImage(
//                               image: AssetImage("assets/images/image.jpg"), 
//                               fit: BoxFit.cover
//                               ),
                          
//                           ),
                          
//                         )
//                       ],
//                     ),
//                   )
                  
//                 ],
//               ),
//             ),
//           ),
//         )
       
      
//       ],
//       ));
//   }
// }


// Widget _buildTextField({required String field, required IconData icon, bool isPassword= false, TextEditingController? controller,}){
// return TextField(
  
//   obscureText: isPassword,
//   controller: controller,
//   style: const TextStyle(
//     color: AppColors.textDark, 
//     ),
//   decoration: InputDecoration(
//     filled: true,
//     fillColor: AppColors.background,
//     hintText: field,
//     hintStyle: TextStyle(
//       color: AppColors.textDark, 
//       fontSize: 14
//     ),
//   prefixIcon: Icon(icon, color:AppColors.lighterblue),
//   contentPadding: EdgeInsets.symmetric(vertical: 16.0),
//   border: OutlineInputBorder(
//     borderRadius: BorderRadius.circular(30),
//     borderSide: BorderSide.none
//   )
//   )
// );
// }
