function changeService(service) {
	if (service === "rutube") {
		document.getElementById("rutube").style.color = "#fff";
		document.getElementById("youtube").style.color = "#000";

		document.getElementById("selector").style.marginLeft = "101px";
		document.getElementById("selector").style.width = "86px";
		document.getElementById("selector").style.backgroundColor = "#000";

		document.getElementById("selector").style.animation =
			"move-blur 0.3s ease-in-out 1";

		setTimeout(() => {
			document.getElementById("selector").style.animation = "";
		}, 500);

		document.getElementById("generateLink").style.backgroundColor = "#000";
	} else {
		document.getElementById("rutube").style.color = "";
		document.getElementById("youtube").style.color = "";

		document.getElementById("selector").style.marginLeft = "";
		document.getElementById("selector").style.width = "";
		document.getElementById("selector").style.backgroundColor = "";

		document.getElementById("selector").style.animation =
			"move-blur 0.3s ease-in-out 1";

		setTimeout(() => {
			document.getElementById("selector").style.animation = "";
		}, 500);

		document.getElementById("generateLink").style.backgroundColor = "";
	}
}

function isInput() {
	if (document.getElementById("input").value.length > 0) {
		document.getElementById("input").style.width = "916px";
		document.getElementById("input").style.borderColor = "#70e000";

		document.getElementById("generateLink").style.left =
			"calc((100% - 1000px) / 2 + 950px)";
		document.getElementById("generateLink").style.transform = "scale(1)";
		document.getElementById("generateLink").style.filter = "blur(0)";
	} else {
		document.getElementById("input").style.width = "";
		document.getElementById("input").style.borderColor = "";

		document.getElementById("generateLink").style.left = "";
		document.getElementById("generateLink").style.filter = "";
		document.getElementById("generateLink").style.transform = "";
	}
}

document.getElementById("input").addEventListener("input", isInput);
