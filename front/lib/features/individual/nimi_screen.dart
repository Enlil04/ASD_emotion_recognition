import 'package:flutter/material.dart';
//import 'package:test_project/classes/ChatClass.dart';
import 'package:flutter_application_1/theme/app_colors.dart';


class NimiScreen extends StatefulWidget {
  const NimiScreen({super.key});

  @override
  State<NimiScreen> createState() => _NimiScreenState();
}

class _NimiScreenState extends State<NimiScreen> {
  
 
  List <Chats> chats =[
    Chats(text: "What's on your mind?", time: "10:30 AM", isUser: false),
    Chats(text: "I have a problem", time: "10:32 AM", isUser: true),
    Chats(text: "Okay here is the solution: something something something something something something something ", time: "10:33 am", isUser: false)
  ];
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.blue.withOpacity(0.08),
      appBar: _builderAppBar(),
      body: Container(
        padding: EdgeInsets.symmetric(horizontal: 15.0, vertical: 0.0),
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                itemCount: chats.length,
                itemBuilder: (context, index){
                  return chatBubble(chats[index]);
                }
                
                )
              ), 
              
              _builderInputArea()
          ],

        ),
      ),
    );
  }
}

PreferredSizeWidget _builderAppBar(){
  return AppBar(
    backgroundColor: AppColors.background,
    toolbarHeight: 80,
    elevation: 0,
    title: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text("Nimi", 
        style: TextStyle(
          color: AppColors.titletext,
          fontWeight: FontWeight.w500, 
          fontSize: 20.0, 
          ),),

        SizedBox(height: 10.0,),
        Text("Your personal companion", 
        style: TextStyle(
          color: AppColors.textDark.withOpacity(0.6), 
          fontSize: 14.0
        ),)
      ],
    ),
  );
}


Widget chatBubble(Chats chat){


  return Padding(
    padding: EdgeInsets.all(15.0),
    child: Column(
      //if user typed it, then it is from right, otherwise right
      crossAxisAlignment:
      chat.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        Container(
          padding: EdgeInsets.symmetric(horizontal: 20.0, vertical: 15.0),
          decoration: BoxDecoration(
           color: AppColors.lighterblue,
           borderRadius: BorderRadius.only(
            topLeft: Radius.circular(15.0), 
            topRight: Radius.circular(15.0),
            bottomLeft: chat.isUser? Radius.circular(15.0): Radius.circular(0.0), 
            bottomRight: chat.isUser? Radius.circular(0.0): Radius.circular(15.0)

           ) 
          ),
          child: Text(chat.text, 
          style: TextStyle(
            color: AppColors.background, 
            fontSize: 16.0, 
            height: 1.4
          ),),
        ), 
        Text(chat.time, 
        style: TextStyle(
          color: AppColors.textDark
        ),)
      ],

    ),
  );

}


Widget _builderInputArea(){

  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 30.0, vertical: 10.0),
    child: Row(children: [
       //Here is the Mic button!!!!!!!!!!
       Container(
        decoration: BoxDecoration(
         border: Border.all(color: AppColors.lighterblue), 
         borderRadius: BorderRadius.circular(10.0)  
        ),
        child: IconButton(onPressed: (){
         
        },
         icon: Icon(Icons.mic_none, color: AppColors.textDark,)),
      ),

      SizedBox(width: 10.0,),

      //This is where the user type !!!!!!!!!!
      Expanded(
        child: TextField(
          decoration: InputDecoration(
            hintText: "Chat with Nimi",
            hintStyle: TextStyle(
              color: AppColors.textDark,
            ),
            filled: true,
            fillColor: AppColors.background,
            contentPadding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
            enabledBorder:OutlineInputBorder(
              borderRadius: BorderRadius.circular(10.0),
              borderSide: BorderSide(color: AppColors.lighterblue)
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10.0),
              borderSide: BorderSide(color: AppColors.lighterblue)
            )
          )
          
          ),
        ),
        SizedBox(width: 12.0,),
      //here is the send button-------------------------------
       Container(
        decoration: BoxDecoration(
          color: AppColors.lighterblue,
          borderRadius: BorderRadius.circular(10.0),
          
        ),
        child: IconButton(onPressed: (){},
         icon: Icon(Icons.send_rounded, 
         color: AppColors.background,)),
      ),     
    ],)
  );
}

//chat dart file
class Chats{
  String text;
  String time;
  bool isUser;


  Chats({required this.text, required this.time, required this.isUser});
}