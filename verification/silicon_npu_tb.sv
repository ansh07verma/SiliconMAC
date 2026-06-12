`ifndef DUMPFILE
`define DUMPFILE "silicon_npu_tb.vcd"
`endif

module silicon_npu_tb #(
    parameter int WIDTH      = 8,
    parameter int ARRAY_SIZE = 4,
    parameter int DEPTH      = 4
);

    localparam int ROW_BITS = $clog2(DEPTH);
    localparam int COL_BITS = $clog2(ARRAY_SIZE);

    logic                    clk;
    logic                    rst_n;
    logic                    start;
    logic [WIDTH-1:0]        weight_wr_data;
    logic [ROW_BITS-1:0]     weight_wr_row;
    logic [COL_BITS-1:0]     weight_wr_col;
    logic                    weight_wr_en;
    logic [WIDTH-1:0]        act_wr_data;
    logic [ROW_BITS-1:0]     act_wr_row;
    logic [COL_BITS-1:0]     act_wr_col;
    logic                    act_wr_en;
    logic [WIDTH*2+$clog2(ARRAY_SIZE)+$clog2(DEPTH)-1:0] result;
    logic                    done;
    logic                    busy;

    silicon_npu #(
        .WIDTH(WIDTH),
        .ARRAY_SIZE(ARRAY_SIZE),
        .DEPTH(DEPTH)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .weight_wr_data(weight_wr_data),
        .weight_wr_row(weight_wr_row),
        .weight_wr_col(weight_wr_col),
        .weight_wr_en(weight_wr_en),
        .act_wr_data(act_wr_data),
        .act_wr_row(act_wr_row),
        .act_wr_col(act_wr_col),
        .act_wr_en(act_wr_en),
        .result(result),
        .done(done),
        .busy(busy)
    );

    always #5 clk = ~clk;

    int pass_count = 0;
    int fail_count = 0;

    task write_row(input int row, input logic [WIDTH-1:0] wval, input logic [WIDTH-1:0] aval);
        for (int c = 0; c < ARRAY_SIZE; c++) begin
            @(posedge clk);
            weight_wr_row = row[ROW_BITS-1:0];
            weight_wr_col = c[COL_BITS-1:0];
            weight_wr_data = wval;
            weight_wr_en  = 1;
            act_wr_row   = row[ROW_BITS-1:0];
            act_wr_col   = c[COL_BITS-1:0];
            act_wr_data   = aval;
            act_wr_en     = 1;
        end
        @(posedge clk);
        weight_wr_en = 0;
        act_wr_en    = 0;
    endtask

    task run_and_check(longint expected);
        @(posedge clk);
        start = 1;
        @(posedge clk);
        start = 0;
        wait (done == 1'b1);
        @(posedge clk);
        #1;
        $display("  result = %0d (expected %0d)", result, expected);
        if (result !== expected) begin
            $display("  FAILED");
            fail_count++;
        end else begin
            $display("  PASS");
            pass_count++;
        end
        #20;
    endtask

    initial begin
        $display("Starting SiliconNPU Testbench");
        $display("WIDTH=%0d, ARRAY_SIZE=%0d, DEPTH=%0d", WIDTH, ARRAY_SIZE, DEPTH);
        $display("----------------------------------------");

        clk = 0;
        rst_n = 0;
        start = 0;
        weight_wr_data = 0;
        weight_wr_row = 0;
        weight_wr_col = 0;
        weight_wr_en = 0;
        act_wr_data = 0;
        act_wr_row = 0;
        act_wr_col = 0;
        act_wr_en = 0;

        #20 rst_n = 1;
        #10;

        // ---- Test 1: Identity ----
        $display("Test 1: Identity (dot product of ones)");
        for (int r = 0; r < DEPTH; r++)
            write_row(r, 1, 1);
        run_and_check(DEPTH * ARRAY_SIZE);

        // ---- Test 2: Zeros ----
        $display("Test 2: All zeros");
        for (int r = 0; r < DEPTH; r++)
            write_row(r, 0, 0);
        run_and_check(0);

        // ---- Test 3: Max values ----
        $display("Test 3: Max values");
        for (int r = 0; r < DEPTH; r++)
            write_row(r, (1 << WIDTH) - 1, (1 << WIDTH) - 1);
        begin
            longint expected = 0;
            for (int r = 0; r < DEPTH; r++)
                for (int c = 0; c < ARRAY_SIZE; c++)
                    expected += ((1 << WIDTH) - 1) * ((1 << WIDTH) - 1);
            run_and_check(expected);
        end

        // ---- Test 4: Weighted sum ----
        $display("Test 4: Weighted sum (2 * 3 per element)");
        for (int r = 0; r < DEPTH; r++)
            write_row(r, 2, 3);
        run_and_check(DEPTH * ARRAY_SIZE * 2 * 3);

        $display("----------------------------------------");
        $display("PASSED: %0d  FAILED: %0d", pass_count, fail_count);
        if (fail_count == 0)
            $display("ALL TESTS PASSED");
        else
            $display("SOME TESTS FAILED");
        $finish;
    end

    string dfile;
    initial begin
        dfile = `DUMPFILE;
        if ($value$plusargs("DUMPFILE=%s", dfile)) ;
        $dumpfile(dfile);
        $dumpvars(0, silicon_npu_tb);
    end

endmodule
