import 'package:flutter/material.dart';
import 'package:flutter_application_1/theme/app_colors.dart';


class GamesScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        title: Text("Mini Games", 
        style: TextStyle(
          color: AppColors.titletext,
          fontWeight: FontWeight.w500, 
          fontSize: 20.0, 
        ),),
      ),
      body: Container(
        padding: EdgeInsets.all(15.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
            children: [
            Text("Let's play some games", 
            style: TextStyle(
              color: AppColors.textDark
            ),), 
            SizedBox(height: 20.0,),
            Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12.0),
                 color: AppColors.lighterblue,
              ),
             
              padding: EdgeInsets.symmetric(horizontal: 20.0, vertical: 20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  Text("Recommended for you",
                  style: TextStyle(
                    color: AppColors.textDark,
                    fontSize: 15.0
                  ),
                  ), 
                  SizedBox(height: 10.0,),
                  Text("Game Name", 
                  style: TextStyle(
                    color: AppColors.textDark,
                    fontSize: 20.0,
                    fontWeight: FontWeight.bold,
                  ),
                  ),
                  SizedBox(height: 10.0,),
                  Text("Description", 
                  style: TextStyle(
                    color: AppColors.textDark,
                    fontSize: 15.0
                  ),), 
                  SizedBox(height: 15.0,),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      TextButton(onPressed: (){},
                        style: TextButton.styleFrom(
                          backgroundColor: AppColors.textDark,
                          foregroundColor: AppColors.background,
                          padding: EdgeInsets.symmetric(horizontal: 30.0, vertical: 15.0)
                        ),
                        child: Text("Play Solo",
                        style: TextStyle(
                        fontWeight: FontWeight.bold
                      ),
                        )),
                        
                        
                      OutlinedButton(onPressed: (){}, 
                      style: OutlinedButton.styleFrom(
                        padding: EdgeInsets.symmetric(horizontal: 30.0, vertical: 15.0),
                        side: BorderSide(
                          color: AppColors.textDark,
                          width: 2.0
                        ),
                        foregroundColor: AppColors.textDark
                      )
                      ,
                      child: Text("With Community", 
                      style: TextStyle(
                        fontWeight: FontWeight.bold
                      ),
                      )),
                    ],
                  )
                   
                ],
              ),
            ), 
            SizedBox(height: 25.0,),
            Text("All Games",
            style: TextStyle(
              color: AppColors.textDark,
              fontWeight: FontWeight.bold,
              fontSize: 15.0
            ),
            ), 
            SizedBox(height: 10.0,),
            Container(
              padding: EdgeInsets.all(20.0),
              decoration: BoxDecoration(
                border: Border.all(color: AppColors.lighterblue,
                width: 2.0,
                style: BorderStyle.solid,
                 ),
                borderRadius: BorderRadius.circular(15.0)
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      Text("Game Name", 
                      style: TextStyle(
                        color: AppColors.lighterblue, 
                        fontSize: 18.0, 
                        fontWeight: FontWeight.bold, 

                      ),),
                      SizedBox(height: 10.0,), 
                      Text("2-3 Players",
                      style: TextStyle(
                        color: AppColors.textDark
                      ),)
                    ],
                  ),
                  Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18.0), 
                      color: AppColors.lighterblue,
                    ), 
                    padding: EdgeInsets.all(8.0),
                    child: Text("Level", 
                    style: TextStyle(
                      color: AppColors.textDark,
                    ),),    
                  )
              
                ],
              ),
            ),



            //------------- SECOND CONTAINER --------------------
            SizedBox(height: 10.0,),
            Container(
              padding: EdgeInsets.all(20.0),
              decoration: BoxDecoration(
                border: Border.all(color: AppColors.lighterblue,
                width: 2.0,
                style: BorderStyle.solid,
                 ),
                borderRadius: BorderRadius.circular(15.0)
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      Text("Game Name", 
                      style: TextStyle(
                        color: AppColors.lighterblue, 
                        fontSize: 18.0, 
                        fontWeight: FontWeight.bold, 

                      ),),
                      SizedBox(height: 10.0,), 
                      Text("2-3 Players",
                      style: TextStyle(
                        color: AppColors.textDark
                      ),)
                    ],
                  ),
                  Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18.0), 
                      color: AppColors.lighterblue,
                    ), 
                    padding: EdgeInsets.all(8.0),
                    child: Text("Level", 
                    style: TextStyle(
                      color: AppColors.textDark,
                    ),),    
                  )
              
                ],
              ),
            ), 



            //----------------THIRD CONTAINER----------------------
            SizedBox(height: 10.0,),
             Container(
              padding: EdgeInsets.all(20.0),
              decoration: BoxDecoration(
                border: Border.all(color: AppColors.lighterblue,
                width: 2.0,
                style: BorderStyle.solid,
                 ),
                borderRadius: BorderRadius.circular(15.0)
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      Text("Game Name", 
                      style: TextStyle(
                        color: AppColors.lighterblue, 
                        fontSize: 18.0, 
                        fontWeight: FontWeight.bold, 

                      ),),
                      SizedBox(height: 10.0,), 
                      Text("2-3 Players",
                      style: TextStyle(
                        color: AppColors.textDark
                      ),)
                    ],
                  ),
                  Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18.0), 
                      color: AppColors.lighterblue,
                    ), 
                    padding: EdgeInsets.all(8.0),
                    child: Text("Level", 
                    style: TextStyle(
                      color: AppColors.textDark,
                    ),),    
                  )
              
                ],
              ),
            ),
          ],
        ),
      ), 
      
    );
  }
}