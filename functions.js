/*
Author: Scott Cunningham

API paths
GET /listChannels?region=[]
GET /insertSCTE?region=[]&chid=[]&duration=[]

*/

// Get the API Gateway URL
var page_url_to_array = window.location.href.split("/");
var api_gateway_url = page_url_to_array.slice(0,4).join("/");

/*
################  API Calls - START
*/

// GET Channel List - Input=region
function get_channel_list(){

  // get selected region
  aws_region = document.getElementById("regiondrop").value;

  console.log("Getting list of channels in region: " + aws_region);

  // concatenate api_gateway_url with listChannels path
  get_channel_list_url = api_gateway_url + "/listChannels?region="+aws_region;


    let dropdown = document.getElementById('channeldrop');
    dropdown.length = 0;

    let defaultOption = document.createElement('option');
    defaultOption.text = 'Select Channel';

    dropdown.add(defaultOption);
    dropdown.selectedIndex = 0;

    var request = new XMLHttpRequest();
    request.open('GET', get_channel_list_url, true);

    request.onload = function() {
      if (request.status === 200) {
        const data = JSON.parse(request.responseText);
        console.log("Get channels list response : " + data)
        let option;
        for (let i = 0; i < data.length; i++) {
          option = document.createElement('option');
          option.text = data[i].ChannelName;
          option.value = data[i].ChannelId;
          dropdown.add(option);
        }
       } else {
        // Reached the server, but it returned an error
        msg = 'An error occurred with the API call - please report this issue to support' + get_channel_list_url
        console.error(msg);
        alert(msg)
      }
    }
    request.send();
}


// GET Channel List - Input=region
function insert_scte35(){

    // get selected region
    aws_region = document.getElementById("regiondrop").value;

    chid = document.getElementById("channeldrop").value;

    duration = document.getElementById("breakdur").value;

    console.log("Attempting to inject SCTE35 ad break for channel "+chid+" in region "+aws_region+" for duration "+duration+": " + aws_region);

    // concatenate api_gateway_url with listChannels path
    scte35_inject_url = api_gateway_url + "/insertSCTE?region="+aws_region+"&chid="+chid+"&duration="+duration;


    var request = new XMLHttpRequest();
    request.open('GET', scte35_inject_url, true);

    request.onload = function() {
      if (request.status === 200) {
        const injectdata = JSON.parse(request.responseText);
        console.log("scte35 inject response : " + injectdata)
        msg = "Ad break injected successfully for duration of : " + duration + "s"
        alert(injectdata['response'])

       } else {
        // Reached the server, but it returned an error
        msg = "Unable to inject SCTE35, received HTTP 500 error from the server"
        const injectdata = JSON.parse(request.responseText);
        console.error(injectdata['response']);
        alert(injectdata['response'])
      }
    }
    request.send();
}

/*
################  API Calls - END
*/