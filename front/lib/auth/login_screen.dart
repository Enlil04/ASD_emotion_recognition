import 'package:flutter/material.dart';
import 'package:flutter_application_1/theme/app_colors.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});
 
  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {

  @override
  Widget build(BuildContext context) {
    return const Login();
  }
}

class Login extends StatelessWidget {
  const Login({super.key,});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Column(
    
      children:[
        //The top title circle
        Container(
          width: double.infinity,
          height: 220,
          decoration: BoxDecoration(
            color: AppColors.background,
            borderRadius: BorderRadius.only(
              bottomLeft: Radius.circular(200.0),
              bottomRight: Radius.circular(200.0)
            ), 
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text("Nimi",
              style: TextStyle(
                color: AppColors.textDark,
                fontWeight: FontWeight.bold,
                fontSize: 35.0,
                letterSpacing: 3.0
              ),),
            ],
          ),
    
        ),
    
        //the actual content
        Expanded(
          child: SingleChildScrollView(
            physics: const BouncingScrollPhysics(),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal:30.0 ),
              child: Column(
                children: [
                  SizedBox(height: 30.0,),
                  Column(
                    children: [
                      Text("login",
                      style: TextStyle(
                        color: AppColors.textDark,
                        fontSize: 24,
                        fontWeight: FontWeight.bold
                      ),),
                      SizedBox(height: 5.0,),
                     Container(
                      width: 80,
                      height: 3,
                      color: AppColors.textDark,
                     ),
                      SizedBox(height: 30.0,)
                    ],
                  ),
                  _buildTextField(
                    field: "Email address",
                    icon: Icons.person_3_outlined,
                  ),
                  SizedBox(height: 16.0,),
                  _buildTextField(field: "Password", icon: Icons.password, isPassword: true),
                    SizedBox(height: 16.0,),
                  _buildTextField(field: "Confirm Password", icon: Icons.password, isPassword: true),
                    SizedBox(height: 16.0,),
              
                  GestureDetector(
                    onTap: (){},
                    child: Text("Don't have an account? Sign up",
                    style: TextStyle(
                      color: AppColors.textDark,
                      decoration: TextDecoration.underline,
                      decorationColor: AppColors.textDark

                    ),),
                  ), 
                  SizedBox(
                    height: 250,
                    child: Stack(
                      alignment: Alignment.bottomCenter,
                      children: [
                        Container(
                          height: 220,
                          width: 220,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: AppColors.background,
                            image: DecorationImage(
                              image: AssetImage("assets/image.png"), 
                              fit: BoxFit.cover
                              ),
                          
                          ),
                          
                        )
                      ],
                    ),
                  )
                  
                ],
              ),
            ),
          ),
        )
       
      
      ],
      ));
  }
}


Widget _buildTextField({required String field, required IconData icon, bool isPassword= false}){
return TextField(
  
  obscureText: isPassword,
  style: const TextStyle(
    color: AppColors.textDark, 
    ),
  decoration: InputDecoration(
    filled: true,
    fillColor: AppColors.background,
    hintText: field,
    hintStyle: TextStyle(
      color: AppColors.textDark, 
      fontSize: 14
    ),
  prefixIcon: Icon(icon, color:AppColors.lighterblue),
  contentPadding: EdgeInsets.symmetric(vertical: 16.0),
  border: OutlineInputBorder(
    borderRadius: BorderRadius.circular(30),
    borderSide: BorderSide.none
  )
  )
);
}
