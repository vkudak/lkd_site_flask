function sp_f1(){
    document.getElementById('spoiler_id').style.display='';
    document.getElementById('show_id').style.display='none';
    }

function sp_f2(){
    document.getElementById('spoiler_id').style.display='none';
    document.getElementById('show_id').style.display='';
    }

function now_time(){
    var currentTime = new Date()
    var hours = currentTime.getHours()
    var minutes = currentTime.getMinutes()
    if (minutes < 10){
        minutes = "0" + minutes
    }
    if (hours < 10){
        hours = "0" + hours
    }
    document.getElementById("ntime").value = hours+":"+minutes;
    }

function get_name(p)
{
    var res=p.split('/').pop();
    document.write( res );
}

function validate_obsForm()
{
    var date=document.forms["add_obs"]["obs_date"].value;
    var desc=document.forms["add_obs"]["obs_desc"].value;
    //var desc = tinymce.get('obs_desc').getContent();
    var content=document.forms["add_obs"]["content"].value;

    if (date==null || date=="")
      {
      alert("Date field must be filled out");
      return false;
      }

    if (desc==null || desc=="")
      {
      alert("Decsription must be filled out");
      return false;
      }

    if (content==null || content=="")
      {
      alert("Add some files!");
      return false;
      }
}