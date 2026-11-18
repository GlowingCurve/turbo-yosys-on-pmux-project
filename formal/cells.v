module dffeas (
    output reg q,
    input d, clk, clrn, prn, ena,
    input asdata, aload, sclr, sload
);
    parameter power_up = "dontcare";
    parameter is_wysiwyg = "false";

    initial begin
        if (power_up == "high") q = 1'b1;
        else if (power_up == "low" || power_up == "dontcare") q = 1'b0;
        else $fatal(1, "Unsupported power_up value");
    end

    // 适用本项目的 prn=1、aload=0 端口配置。
    always @(posedge clk or negedge clrn) begin
        if (!clrn) q <= 1'b0;
        else if (ena) begin
            if (sclr) q <= 1'b0;
            else if (sload) q <= asdata;
            else q <= d;
        end
    end
endmodule

module cycloneiv_lcell_comb (
    output combout, cout,
    input dataa, datab, datac, datad, cin
);
    parameter lut_mask = 16'hffff;
    parameter dont_touch = "off";
    parameter lpm_type = "cycloneiv_lcell_comb";
    parameter sum_lutc_input = "datac";

    initial begin
        if (sum_lutc_input != "datac" && sum_lutc_input != "cin")
            $fatal(1, "Unsupported sum_lutc_input value");
    end

    wire lut_c = (sum_lutc_input == "cin") ? cin : datac;
    assign combout = lut_mask[{datad, lut_c, datab, dataa}];
    assign cout = lut_mask[{1'b0, cin, datab, dataa}];
endmodule
