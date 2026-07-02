const logo = "/assets/logo-a1b2c3.svg";
const model = "/assets/model-a1b2c3.glb";
import("/assets/chunk-d4e5f6.js").then(() => console.log("chunk loaded"));
document.getElementById("root").innerHTML = `<main class="hero"><h1>Single HTML Build Demo</h1><img src="${logo}" alt="logo"><p>${model}</p></main>`;

// Vite/esbuild may convert ordinary string paths into static template literals.
var BUILDING_IMAGES=[`/buildings/buildingA.jpg`,`/buildings/buildingB.jpg`,`/buildings/portal.jpg`,`/buildings/foundation.jpg`,`/buildings/joint.jpg`];
const unresolvedDynamic=`/buildings/${buildingName}.jpg`;
window.setBuildingImage=function(buildingIndex){const imgEl=document.getElementById("building-detail"); if(imgEl) imgEl.src=BUILDING_IMAGES[buildingIndex]||BUILDING_IMAGES[0];};
