// ---- UIKit expects browser globals ----
global.self = global;
global.window = {};
global.document = {};

const express = require("express");
const { generateKitTokenForTest } = require("@zegocloud/zego-uikit-prebuilt");

const app = express();

const APP_ID = Number(process.env.ZEGOCLOUD_APP_ID);
const SERVER_SECRET = process.env.ZEGOCLOUD_SERVER_SECRET;

if (!APP_ID || !SERVER_SECRET) {
  console.error("❌ ZEGOCLOUD env vars not set");
  process.exit(1);
}

app.get("/kit-token", (req, res) => {
  const { room_id, user_id } = req.query;

  if (!room_id || !user_id) {
    return res.status(400).json({ error: "Missing params" });
  }

  try {
    const kitToken = generateKitTokenForTest(
      APP_ID,
      SERVER_SECRET,
      room_id,
      user_id,
      3600
    );

    console.log("✅ KitToken length:", kitToken.length);
    res.json({ kitToken });
  } catch (e) {
    console.error("❌ Token generation failed", e);
    res.status(500).json({ error: "Token generation failed" });
  }
});

app.listen(5050, () => {
  console.log("✅ Zego token service running on http://127.0.0.1:5050");
});
