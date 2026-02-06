import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import 'therapist_signup.dart';
import 'parent_signup.dart';
import 'user_signup.dart';


class SignUp extends StatefulWidget {
  const SignUp({super.key});

  @override
  State<SignUp> createState() => _SignUpState();
}

class _SignUpState extends State<SignUp> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.lighterblue,
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
                  SizedBox(height: 50.0,),
                  Text("Sign up as : ", 
                  style: TextStyle(
                    color: AppColors.titletext, 
                    fontSize: 20.0, 
                    fontWeight: FontWeight.bold,
                   
                  ),),
                  SizedBox(height: 30.0,),

                  DropdownMenu(
                    textStyle: TextStyle(
                      color: AppColors.textDark, 
                      fontSize: 16.0,
                    ),
                    dropdownMenuEntries: [
                      _builderEntry("User"),
                      _builderEntry("Parent"),
                      _builderEntry("Therapist")
                    ],
                    width: 300,
                    hintText: "Select a role",
                    textAlign: TextAlign.center,
                    menuStyle: MenuStyle(
                      backgroundColor: WidgetStatePropertyAll(AppColors.background),
                      elevation: WidgetStatePropertyAll(2),
                      shape: WidgetStatePropertyAll(
                        RoundedRectangleBorder(borderRadius: BorderRadiusGeometry.circular(20.0))
                      )
                    ),
                    inputDecorationTheme: InputDecorationTheme(
                      hintStyle: TextStyle(
                      color: AppColors.textDark, 
                    ),
                    filled: true,
                    fillColor: AppColors.background,
                    contentPadding: EdgeInsets.symmetric(vertical: 16.0),
                    //unclicked
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(25.0),
                      borderSide: const BorderSide(color: AppColors.textDark, width: 1.5), ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(25.0),
                      borderSide: const BorderSide(color: AppColors.titletext, width: 2.0)),
                    
                    
                    ),
                    onSelected: (value) => {
                      if(value == "Therapist"){
                        Navigator.push(
                          context, 
                          MaterialPageRoute(builder: (context)=> const TherapistSignUp()))
                      }
                      else if (value == "Parent"){
                        Navigator.push(context, 
                        MaterialPageRoute(builder: (context) => const ParentSignUp()))
                      }
                      else if(value =="User"){
                        Navigator.push(context, 
                        MaterialPageRoute(builder: (context) => const UserSignUp()))
                      }
                    },
                    ),
                    SizedBox(height: 20.0,),
                  GestureDetector(
                    onTap: (){
                     Navigator.pop(context);
                    },
                    child: Text("Already have an account? Login",
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
      )

    );
  }
}




DropdownMenuEntry _builderEntry(String entry){
  return DropdownMenuEntry(value: entry, label: entry,
  style: ButtonStyle(
    alignment: Alignment.center,
    foregroundColor: WidgetStatePropertyAll(AppColors.titletext),
    textStyle: WidgetStatePropertyAll(
      const TextStyle(
        fontSize: 16.0
      ),
    ),
    backgroundColor: WidgetStateProperty.resolveWith((state){
       if (state.contains(WidgetState.pressed) || state.contains(WidgetState.hovered) || state.contains(WidgetState.selected)){
        return AppColors.blue;
      }
      return AppColors.background;
    })
    
  ));
}