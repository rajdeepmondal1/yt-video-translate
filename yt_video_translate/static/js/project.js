/* Project specific Javascript goes here. */
// $(document).ready(function () {
//     $("#input_form").submit(function () {
//         $("#form_container").attr("style", "display: none");
//         $("#hidden_section").attr("style", "display: block");
//         return true;
//     });
// });

// document.getElementById("translate_onclick").onclick = function () {
const url = `${location.pathname}/status/`;
const redirectURL = `${location.pathname}/translated/`;
const checkStatus = () => {
  console.log("Checking article status.");
  fetch(url).then((resp) => {
    console.log("Got article status:", resp.status);
    if (resp.status == 200) {
      console.log("Article ready - refresh page.");
      //   location.reload();
      location.assign(redirectURL);
    } else {
      console.log("Article processing - wait.");
    }
  });
};
checkStatus();
setInterval(checkStatus, 2000);
// };

var start = document.getElementById("translate_button"),
  current_progress = 0,
  step = 0.5; // the smaller this is the slower the progress bar

start.onclick = function () {
  interval = setInterval(function () {
    current_progress += step;
    progress =
      Math.round((Math.atan(current_progress) / (Math.PI / 2)) * 100 * 1000) /
      1000;
    $(".progress-bar")
      .css("width", progress + "%")
      .attr("aria-valuenow", progress)
      .text(progress + "%");
    if (progress >= 100) {
      clearInterval(interval);
    } else if (progress >= 70) {
      step = 0.1;
    }
  }, 100);
};
