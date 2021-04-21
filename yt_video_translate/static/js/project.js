const url = `${location.pathname}/status/`;
const redirectURL = `${location.pathname}/translated/`;
const checkStatus = () => {
  console.log("Checking article status.");
  fetch(url).then((resp) => {
    console.log("Got article status:", resp.status);
    if (resp.status == 200) {
      console.log("Article ready - refresh page.");
      location.assign(redirectURL);
    } else {
      console.log("Article processing - wait.");
    }
  });
};
checkStatus();
setInterval(checkStatus, 2000);

var Tawk_API = Tawk_API || {},
  Tawk_LoadStart = new Date();
(function () {
  var s1 = document.createElement("script"),
    s0 = document.getElementsByTagName("script")[0];
  s1.async = true;
  s1.src = "https://embed.tawk.to/60803cac5eb20e09cf353a94/1f3qeq0rf";
  s1.charset = "UTF-8";
  s1.setAttribute("crossorigin", "*");
  s0.parentNode.insertBefore(s1, s0);
})();
