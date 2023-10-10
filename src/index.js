import React from "react";
import ReactDOM from "react-dom";
import "./style/index.css";
import App from "./components/App";
import { BrowserRouter as Router } from "react-router-dom";

ReactDOM.render(
  <Router basename="/paramore">
    <React.StrictMode>
      <App />
    </React.StrictMode>
  </Router>,
  document.getElementById("root")
);
