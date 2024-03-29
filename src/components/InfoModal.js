// @flow
import "../style/InfoModal.css";
import { isMobile } from "./utils";
import { ModalText } from "./constants";
import React from "react";

const mobile = isMobile();

type InfoModalProps = {
  handler: () => void,
  display: boolean,
};

export default function InfoModal({ handler, display }: InfoModalProps): React$MixedElement {
  const clickOutHandler = (event: any) => {
    if (event.target.className !== "ModalBox") {
      handler();
    }
  };

  return (
    <div className="InfoModal" onClick={clickOutHandler} style={{ display: display ? "block" : "none" }}>
      <div className={mobile ? "ModalBox ModalBox-mobile" : "ModalBox"}>
        <p dangerouslySetInnerHTML={{ __html: ModalText }} />
        <p style={{ fontSize: "14px" }}>
          Re-made for Paramore and Hayley Williams by Renee. If you have comments or
          suggestions, my Twitter is <a href="https://twitter.com/renaateste">@renaateste</a>!
        </p>
        {/** CREDITS: Please do not edit this. Feel free to add your own credits to ModalText. */}
        <p style={{ fontSize: "14px" }}>
          Made by&nbsp;<a href="http://shaynak.github.io">Shayna Kothari</a>
          &nbsp;using&nbsp;
          <a href="http://reactjs.org">React</a>. Lyrics scraped from&nbsp;
          <a href="http://genius.com">Genius</a>&nbsp; using&nbsp;
          <a href="https://github.com/johnwmillr/LyricsGenius">LyricsGenius</a>. If you have comments or suggestions, contact her by{" "}
          <a href="mailto:shayna.kothari@berkeley.edu">email</a>!
        </p>
      </div>
    </div>
  );
}
