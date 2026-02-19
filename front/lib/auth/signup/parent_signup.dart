import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../login_screen.dart';
import '../../services/api_service.dart';
class ParentSignUp extends StatefulWidget {
  const ParentSignUp({super.key});

  @override
  State<ParentSignUp> createState() => _ParentSignUpState();
}

class _ParentSignUpState extends State<ParentSignUp> {
    final _firstNameC = TextEditingController();
  final _lastNameC = TextEditingController();
  final TextEditingController _dateOfBirthController = TextEditingController();
  final _usernameC = TextEditingController();
  final _emailC = TextEditingController();
  final _pwC = TextEditingController();
  final _pw2C = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
      _firstNameC.dispose();
    _lastNameC.dispose();
    _usernameC.dispose();
    _emailC.dispose();
    _pwC.dispose();
    _pw2C.dispose();
    _dateOfBirthController.dispose();
    super.dispose();
  }

  Future<void> _selectDate(BuildContext context) async{
    final DateTime? picked = await showDatePicker(
      context: context, 
      initialDate: DateTime.now(),
      firstDate: DateTime(1900), 
      lastDate: DateTime.now(),
      builder: (context, child) {
        return Theme(
          data: ThemeData().copyWith(
            colorScheme: ColorScheme.light(
              primary: AppColors.titletext,
              onPrimary: AppColors.blue,
              surface: AppColors.background,
              onSurface: AppColors.titletext

            ),
            dialogTheme: DialogThemeData(
              backgroundColor: AppColors.background
            ) 
          ), 
          child: child!);
      },
    );
      if(picked != null){
        setState(() {
          _dateOfBirthController.text = "${picked.year}-${picked.month}-${picked.day}";
        });
      }
  }
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
                color: AppColors.titletext,
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
                      Text("Sign Up",
                      style: TextStyle(
                        color: AppColors.titletext,
                        fontSize: 24,
                        fontWeight: FontWeight.bold
                      ),),
                      SizedBox(height: 5.0,),
                     Container(
                      width: 80,
                      height: 3,
                      color: AppColors.titletext,
                     ),
                      SizedBox(height: 30.0,)
                    ],
                  ),
                  IconButton(onPressed: (){},
                   icon: Icon(Icons.person_2_rounded, color: AppColors.textDark,),
                   style: ButtonStyle(
                    backgroundColor: WidgetStatePropertyAll(AppColors.background),
                    iconSize: WidgetStatePropertyAll(90.0)
                   ), ),SizedBox(height: 16.0,),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(child: _buildTextField(field: "First Name", icon: Icons.person_3_outlined, controller: _firstNameC)),
                      SizedBox(width: 10.0,),
                      Expanded(child: _buildTextField(field: "Last Name", icon: Icons.person_3_outlined, controller:_lastNameC))
                    ],
                  ),
                  SizedBox(height: 16.0,),
                  _buildTextField(
                    field: "Username",
                    icon: Icons.person_3_outlined,
                     controller: _usernameC,
                  ),
                  SizedBox(height: 16.0,),
                  _buildTextField(field: "Password", icon: Icons.password, isPassword: true, controller: _pwC,),
                    SizedBox(height: 16.0,),
                  _buildTextField(field: "Confirm Password", icon: Icons.password, isPassword: true, controller: _pw2C,),
                    SizedBox(height: 16.0,),
                  _buildTextField(field: "Date of birth", 
                  icon: Icons.date_range,
                   controller: _dateOfBirthController,
                   readOnly: true,
                   onTap: ()=> _selectDate(context)
                  ),
                  SizedBox(height: 16.0,),
                  _buildTextField(field: "Email", icon: Icons.email_rounded, controller: _emailC,),
                  SizedBox(height: 16.0,),

                    ElevatedButton(
                  onPressed: _loading ? null : () async {
                      final first = _firstNameC.text.trim();
                      final last = _lastNameC.text.trim();
                      final username = _usernameC.text.trim();
                      final email = _emailC.text.trim();
                      final pw = _pwC.text;
                      final pw2 = _pw2C.text;
                      final dob = _dateOfBirthController.text.trim();

                      if (first.isEmpty || last.isEmpty ||username.isEmpty || email.isEmpty || pw.isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text("Fill username, email, and password.")),
                        );
                        return;
                      }

                      if (pw != pw2) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text("Passwords do not match.")),
                        );
                        return;
                      }

                      setState(() => _loading = true);
                      try {
                        await ApiService.register(
                          email: email,
                          password: pw,
                          role: "parent",
                          username: username,
                          name: "$first $last",
                          dob: dob.isEmpty ? null : dob,
                          extra: {"child_count": 1}, // optional
                        );

                        if (!mounted) return;

                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text("Account created. Please login.")),
                        );

                        Navigator.pushReplacement(
                          context,
                          MaterialPageRoute(builder: (_) => const LoginPage()),
                        );
                      } catch (e) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text(e.toString())),
                        );
                      } finally {
                        if (mounted) setState(() => _loading = false);
                      }
                    },

                  child: Text("Sign Up",
                  style: TextStyle(
                    color: AppColors.background,
                    fontWeight: FontWeight.bold,
                    fontSize: 15.0
                  ),),
                  style: ButtonStyle(
                    backgroundColor: WidgetStatePropertyAll(AppColors.textDark),
                    padding: WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: 140.0, vertical: 15.0))
                  ),),
                 SizedBox(height: 16.0,),
                  
                  GestureDetector(
                    onTap: (){
                       Navigator.push(context,
                       MaterialPageRoute(builder: (context) => const LoginPage()));
                    },
                    child: Text("Already have an account? Login",
                    style: TextStyle(
                      color: AppColors.titletext,
                      decoration: TextDecoration.underline,
                      decorationColor: AppColors.titletext

                    ),),
                  ), 
                 
                  
                  
                ],
              ),
            ),
          ),
        )
       
      
      ],
      ));
  }
}



Widget _buildTextField({required String field, 
required IconData icon, 
bool isPassword= false,
TextEditingController? controller,
bool readOnly=false,
VoidCallback? onTap}){
return TextField(
  controller: controller,
  onTap: onTap,
  readOnly: readOnly,
  obscureText: isPassword,
  style: const TextStyle(
    color: AppColors.textDark
    ),
  decoration: InputDecoration(
    filled: true,
    fillColor: const Color(0xFFFAFCFB),
    hintText: field,
    hintStyle: TextStyle(
      color: AppColors.textDark, 
      fontSize: 14
    ),
  prefixIcon: Icon(icon, color:const Color(0xFFB7CEDE)),
  contentPadding: EdgeInsets.symmetric(vertical: 16.0),
  border: OutlineInputBorder(
    borderRadius: BorderRadius.circular(30),
    borderSide: BorderSide.none
  )
  )
);
}
