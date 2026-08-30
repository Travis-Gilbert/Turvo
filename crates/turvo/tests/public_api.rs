#[test]
fn builder_returns_the_turvo_runtime() {
  fn accepts_turvo_builder(_: tauri::Builder<turvo::Turvo>) {}

  accepts_turvo_builder(turvo::builder());
}

#[test]
fn reported_servo_version_matches_the_exact_manifest_pin() {
  let manifest = include_str!("../Cargo.toml");
  let expected = format!("servo = \"={}\"", turvo::SERVO_VERSION);

  assert!(
    manifest
      .lines()
      .any(|line| line.trim() == expected.as_str()),
    "{expected} is missing from crates/turvo/Cargo.toml"
  );
}
