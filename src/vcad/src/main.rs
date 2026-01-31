//! Vial label applicator components built with vcad.
//!
//! Generates simplified versions of each component as STL files.
//! These lack BREP fillets (vcad is mesh-based) but are suitable for
//! Blender MCP import and rapid prototyping.

mod config;
mod dancer_arm;
mod frame;
mod guide_roller_bracket;
mod peel_plate;
mod spool_holder;
mod vial_cradle;

fn main() {
    let output_dir = "../../models/vcad";
    std::fs::create_dir_all(output_dir).expect("Failed to create output directory");

    let cfg = config::load_config();

    println!("Building vcad components...\n");

    type BuildFn = Box<dyn Fn(&config::Config) -> vcad::Part>;
    let components: Vec<(&str, BuildFn)> = vec![
        ("peel_plate", Box::new(peel_plate::build)),
        ("vial_cradle", Box::new(vial_cradle::build)),
        ("main_frame", Box::new(frame::build)),
        ("spool_holder", Box::new(spool_holder::build)),
        ("dancer_arm", Box::new(dancer_arm::build)),
        ("guide_roller_bracket", Box::new(guide_roller_bracket::build)),
    ];

    for (name, build_fn) in &components {
        let part = build_fn(&cfg);
        let path = format!("{}/{}.stl", output_dir, name);
        part.write_stl(&path)
            .unwrap_or_else(|e| panic!("Failed to write {} STL: {}", name, e));
        println!("Exported: {}", path);
    }

    println!("\nAll vcad components built.");
}
