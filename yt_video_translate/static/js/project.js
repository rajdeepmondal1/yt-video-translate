/* Project specific Javascript goes here. */
// $(document).ready(function () {
//     $("#input_form").submit(function () {
//         $("#form_container").attr("style", "display: none");
//         $("#hidden_section").attr("style", "display: block");
//         return true;
//     });
// });

const url = `${location.pathname}status/`;
const redirectURL = `${location.pathname}translated`;
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
