\version "2.26.0"

\score {
  \new Staff \relative c' {
    \repeat volta 2 {
      c4 ( d e f
      <g b>2-. ) <a c>4-. r4
    }
    \bar "|."
  }
}
